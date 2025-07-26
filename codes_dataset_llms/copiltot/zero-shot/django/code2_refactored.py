VALID_IP_ADDRESS_ERROR = _("Enter a valid %(protocol)s address.")

def validate_ipv4_address(value):
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise ValidationError(
            VALID_IP_ADDRESS_ERROR,
            code="invalid",
            params={"protocol": _("IPv4"), "value": value},
        )