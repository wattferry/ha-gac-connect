import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from gac_connect.const import REGIONS
from gac_connect.errors import LoginError
from custom_components.gac_connect.api import GacClient, local_mobile


@pytest.mark.parametrize("region", list(REGIONS))
def test_local_61_prefix_is_not_an_australian_country_code(region):
    assert local_mobile("612345678", REGIONS[region]["tel"]) == "612345678"


@pytest.mark.parametrize("region,number,expected", [
    ("HK", "61234567", "61234567"), ("HK", "+852 6123 4567", "61234567"),
    ("AU", "+61 412 345 678", "412345678"), ("AU", "0412345678", "412345678"),
    ("NZ", "+64 21 123 4567", "211234567"), ("GB", "0044 7700 900123", "7700900123"),
    ("TH", "+66 61 234 5678", "612345678"),
])
def test_sms_and_login_send_same_regional_number(region, number, expected):
    client = GacClient(region, Mock())
    client._verify_captcha = AsyncMock(return_value=Mock())
    client._main_call = AsyncMock(side_effect=[
        {"success": True, "data": {"verifyCodeTicket": "ticket"}},
        {"success": True, "data": {"token": "main", "refreshToken": "next"}},
    ])
    client._establish_iov = AsyncMock()
    async def run():
        await client.request_sms(number, 10)
        await client.login_sms(number, "123456")
    asyncio.run(run())
    for call in client._main_call.await_args_list:
        assert call.args[1]["mobile"] == expected
        assert call.args[1]["countryTelCode"] == REGIONS[region]["tel"]


@pytest.mark.parametrize("number", ["+447700900123", "", "words", "000", True])
def test_invalid_or_wrong_region_number_does_not_consume_captcha(number):
    client = GacClient("AU", Mock())
    client._verify_captcha = AsyncMock()
    with pytest.raises(LoginError):
        asyncio.run(client.request_sms(number, 10))
    client._verify_captcha.assert_not_called()
