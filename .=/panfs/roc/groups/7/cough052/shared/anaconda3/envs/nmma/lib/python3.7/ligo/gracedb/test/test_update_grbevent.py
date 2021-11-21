import pytest
try:
    from unittest import mock
except ImportError:  # py < 3
    import mock


def test_update_grbevent_no_args_provided(safe_client):
    err_str = ('Provide at least one of ra, dec, error_radius, t90, '
               'redshift, or designation')
    with pytest.raises(ValueError, match=err_str):
        safe_client.update_grbevent('E123456')


GRBEVENT_DATA = [
    (1, None, None, None, None, None),
    (None, 2, 3, None, 5, 'test'),
    (1, 2, 3, 4, 5, 'test'),
]
@pytest.mark.parametrize(  # noqa: E302
    "ra,dec,error_radius,t90,redshift,designation",
    GRBEVENT_DATA
)
def test_update_grbevent_with_args(
    safe_client, ra, dec, error_radius, t90, redshift, designation
):

    with mock.patch.object(safe_client, 'patch') as mock_patch, \
         mock.patch('ligo.gracedb.rest.GraceDb.templates',  # noqa: E127
                    new_callable=mock.PropertyMock):
        safe_client.update_grbevent(
            'E123456', ra=ra, dec=dec, error_radius=error_radius, t90=t90,
            redshift=redshift, designation=designation
        )

    # Check calls to patch() method
    call_args, call_kwargs = mock_patch.call_args
    assert len(call_kwargs) == 1
    assert 'data' in call_kwargs

    # Construct expected body content
    expected_body = {}
    if ra is not None:
        expected_body['ra'] = ra
    if dec is not None:
        expected_body['dec'] = dec
    if error_radius is not None:
        expected_body['error_radius'] = error_radius
    if t90 is not None:
        expected_body['t90'] = t90
    if redshift is not None:
        expected_body['redshift'] = redshift
    if designation is not None:
        expected_body['designation'] = designation

    assert call_kwargs['data'] == expected_body
