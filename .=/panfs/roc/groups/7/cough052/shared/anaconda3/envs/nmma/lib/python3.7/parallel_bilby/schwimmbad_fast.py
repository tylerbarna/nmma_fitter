import atexit
import datetime
import json
import sys
import timeit
import traceback

from schwimmbad import _VERBOSE, MPIPool, log


def _dummy_callback(x):
    pass


def _import_mpi(quiet=False, use_dill=False):
    global MPI
    try:
        import mpi4py

        mpi4py.rc.threads = False
        mpi4py.rc.recv_mprobe = False
        from mpi4py import MPI as _MPI

        if use_dill:
            import dill

            _MPI.pickle.__init__(dill.dumps, dill.loads, dill.HIGHEST_PROTOCOL)
        MPI = _MPI
    except ImportError:
        if not quiet:
            # Re-raise with a more user-friendly error:
            raise ImportError("Please install mpi4py")

    return MPI


class MPIPoolFast(MPIPool):
    """A processing pool with persistent MPI tasks.

    Schwimmbad's MPI Pool starts the worker threads waiting in __init__
    but then finally does sys.exit(0), so those threads never get a
    chance to do anything else.

    This fix will behave like MPIPool as default, but using the
    parameters, the MPI worker tasks can be allowed to persist
    beyond the pool.
    """

    def __init__(
        self,
        comm=None,
        use_dill=False,
        begin_wait=True,
        persistent_tasks=True,
        parallel_comms=False,
        time_mpi=False,
        timing_interval=0,
    ):
        MPI = _import_mpi(use_dill=use_dill)

        if comm is None:
            comm = MPI.COMM_WORLD
        self.comm = comm

        self.master = 0
        self.rank = self.comm.Get_rank()

        atexit.register(lambda: MPIPool.close(self))

        # Option to enable parallel communication
        self.parallel_comms = parallel_comms

        # Initialise timer
        self.time_mpi = time_mpi
        if self.time_mpi:
            self.timer = Timer(self.rank, self.comm, self.master)
        else:
            self.timer = NullTimer()

        # Periodically save the timing output (specify in seconds)
        self.timing_interval = 0
        if self.comm.size > 32:  # Choose a worker from a different node if possible
            if self.rank == 32:
                self.timing_interval = timing_interval
        else:
            if self.rank == 1:
                self.timing_interval = timing_interval

        if self.timing_interval == 0:
            self.timing_interval = False

        if not self.is_master():
            if begin_wait:
                # workers branch here and wait for work
                try:
                    self.wait()
                except Exception:
                    print(f"worker with rank {self.rank} crashed".center(80, "="))
                    traceback.print_exc()
                    sys.stdout.flush()
                    sys.stderr.flush()
                    # shutdown all mpi tasks:
                    from mpi4py import MPI

                    MPI.COMM_WORLD.Abort()
                finally:
                    if not persistent_tasks:
                        sys.exit(0)

        else:
            self.workers = set(range(self.comm.size))
            self.workers.discard(self.master)
            self.size = self.comm.Get_size() - 1

            if self.size == 0:
                raise ValueError(
                    "Tried to create an MPI pool, but there "
                    "was only one MPI process available. "
                    "Need at least two."
                )

    @staticmethod
    def enabled():
        if MPI is None:
            _import_mpi(quiet=True)
        if MPI is not None:
            if MPI.COMM_WORLD.size > 1:
                return True
        return False

    def wait(self, callback=None):
        """Tell the workers to wait and listen for the master process. This is
        called automatically when using :meth:`MPIPool.map` and doesn't need to
        be called by the user.
        """
        if self.is_master():
            return

        worker = self.comm.rank
        status = MPI.Status()

        if self.timing_interval:
            time_snapshots = []
            self.timer.start("walltime")

        # Flag if master is performing a serial task (True by default)
        master_serial = True
        self.timer.start("master_serial")

        while True:
            # Receive task
            self.timer.start(
                "mpi_recv"
            )  # recv timer only gets counted if entering into a parallel task
            if not master_serial:
                self.timer.start(
                    "barrier"
                )  # start the barrier timer in case this is the last parallel task

            log.log(_VERBOSE, f"Worker {worker} waiting for task")
            task = self.comm.recv(source=self.master, tag=MPI.ANY_TAG, status=status)

            # Indicator from master that a serial task is being performed
            if task == "s":
                self.timer.stop("barrier")  # count recv time towards barrier
                self.timer.start("master_serial")
                master_serial = True
            elif task == "p":
                self.timer.stop("master_serial")
                master_serial = False
            else:
                # Process task
                if task is None:
                    log.log(_VERBOSE, f"Worker {worker} told to quit work")

                    if master_serial:
                        self.timer.stop("master_serial")
                    else:
                        self.timer.stop("barrier")

                    break

                if master_serial and self.time_mpi:
                    print(
                        "Warning: Serial section has been flagged, but not unflagged yet. Timing will be inaccurate."
                    )
                self.timer.stop("mpi_recv")

                self.timer.start("compute")
                func, arg = task
                log.log(
                    _VERBOSE,
                    f"Worker {worker} got task {arg} with tag {status.tag}",
                )

                result = func(arg)
                self.timer.stop("compute")

                # Return results
                self.timer.start("mpi_send")
                log.log(
                    _VERBOSE,
                    f"Worker {worker} sending answer {result} with tag {status.tag}",
                )

                self.comm.ssend(result, self.master, status.tag)
                self.timer.stop("mpi_send")

                if self.timing_interval:
                    self.timer.stop("walltime")
                    if self.timer.interval_time["walltime"] > self.timing_interval:
                        time_snapshots += [self.timer.interval_time.copy()]
                        self.timer.reset()
                    self.timer.start("walltime")

        if self.timing_interval:
            with open("mpi_worker_timing.json", "w") as f:
                json.dump(time_snapshots, f)

        if callback is not None:
            callback()

    def map(self, worker, tasks, callback=None):
        """Evaluate a function or callable on each task in parallel using MPI.

        The callable, ``worker``, is called on each element of the ``tasks``
        iterable. The results are returned in the expected order (symmetric with
        ``tasks``).

        Parameters
        ----------
        worker : callable
            A function or callable object that is executed on each element of
            the specified ``tasks`` iterable. This object must be picklable
            (i.e. it can't be a function scoped within a function or a
            ``lambda`` function). This should accept a single positional
            argument and return a single object.
        tasks : iterable
            A list or iterable of tasks. Each task can be itself an iterable
            (e.g., tuple) of values or data to pass in to the worker function.
        callback : callable, optional
            An optional callback function (or callable) that is called with the
            result from each worker run and is executed on the master process.
            This is useful for, e.g., saving results to a file, since the
            callback is only called on the master thread.

        Returns
        -------
        results : list
            A list of results from the output of each ``worker()`` call.
        """

        # If not the master just wait for instructions.
        if not self.is_master():
            self.wait()
            return

        if callback is None:
            callback = _dummy_callback

        workerset = self.workers.copy()
        tasklist = [(tid, (worker, arg)) for tid, arg in enumerate(tasks)]
        resultlist = [None] * len(tasklist)
        pending = len(tasklist)

        # Buffers for each worker (worker index starts from 1)
        reqlist = [None] * len(workerset)
        taskbuffer = [None] * len(workerset)

        self.flag_parallel()

        while pending:
            if workerset and tasklist:
                worker = workerset.pop()
                ibuf = worker - 1
                taskid, taskbuffer[ibuf] = tasklist.pop()
                log.log(
                    _VERBOSE,
                    "Sent task %s to worker %s with tag %s",
                    taskbuffer[ibuf][1],
                    worker,
                    taskid,
                )
                # Create send request - no need to test because result return is a sufficient indicator
                reqlist[ibuf] = self.comm.isend(
                    taskbuffer[ibuf], dest=worker, tag=taskid
                )
                if not self.parallel_comms:
                    reqlist[ibuf].wait()

            if tasklist:
                flag = self.comm.Iprobe(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG)
                if not flag:
                    continue
            else:
                self.comm.Probe(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG)

            status = MPI.Status()
            result = self.comm.recv(
                source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status
            )
            worker = status.source
            taskid = status.tag
            log.log(
                _VERBOSE, "Master received from worker %s with tag %s", worker, taskid
            )

            callback(result)

            workerset.add(worker)
            resultlist[taskid] = result
            pending -= 1

        self.flag_serial()

        return resultlist

    def close(self):
        """When master task is done, tidy up."""

        if self.is_master():
            self.kill_workers()

        if self.time_mpi:
            self.timer.parallel_total()

    def kill_workers(self):
        """Tell all the workers to quit."""
        buf = None
        for worker in self.workers:
            self.comm.send(buf, dest=worker, tag=0)

    def flag_serial(self):
        """Tell all the workers that serial code is being executed."""
        if self.time_mpi:
            buf = "s"
            for worker in self.workers:
                self.comm.send(buf, dest=worker, tag=0)

    def flag_parallel(self):
        """Tell all the workers that serial code has finished."""
        if self.time_mpi:
            buf = "p"
            for worker in self.workers:
                self.comm.send(buf, dest=worker, tag=0)


class Timer:
    def __init__(self, rank, comm, master):

        self.rank = rank
        self.comm = comm
        self.master = master

        self.cumulative_time = {}
        self.interval_time = {}
        self.start_time = {}
        self.total = {}

        self.group = [
            "master_serial",
            "mpi_recv",
            "compute",
            "mpi_send",
            "barrier",
            "walltime",
        ]

        self.reset_all()

    def start(self, name):
        self.start_time[name] = timeit.time.perf_counter()

    def stop(self, name):
        now = timeit.time.perf_counter()
        dt = now - self.start_time[name]
        self.interval_time[name] += dt
        self.cumulative_time[name] += dt

    def reset_all(self):
        for name in self.group:
            self.start_time[name] = 0
            self.cumulative_time[name] = 0
        self.reset()

    def reset(self):
        for name in self.group:
            self.interval_time[name] = 0

    def parallel_total(self):
        if self.rank == self.master:
            for name in self.group:
                self.total[name] = 0

            status = MPI.Status()
            for isrc in range(1, self.comm.Get_size()):
                times = self.comm.recv(source=isrc, tag=1, status=status)
                for name in self.group:
                    self.total[name] += times[name]

            print("MPI Timer -- cumulative wall time of each task")
            all = 0
            for name in self.group:
                if name == "walltime":
                    continue
                all += self.total[name]
            for name in self.group:
                str_time = str(datetime.timedelta(seconds=self.total[name]))
                str_percent = f"{100*self.total[name] / all:.2f}%"
                print(f"  {name: <16}: {str_time: <10} ({str_percent: <5})")
            print(f"  Total time: {str(datetime.timedelta(seconds=all))} ({all:.2f} s)")

        else:
            self.comm.send(self.cumulative_time, dest=self.master, tag=1)


class NullTimer(Timer):
    def __init__(self):
        return

    def start(self, name):
        return

    def stop(self, name):
        return

    def reset(self):
        return

    def reset_all(self):
        return

    def parallel_total(self):
        return

    def __str__(self):
        return ""
