def validate_ipv4_address(value):
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise ValidationError(
            _("Enter a valid %(protocol)s address."),
            code="invalid",
            params={"protocol": _("IPv4"), "value": value},
        )