def check_models_permissions(app_configs=None):
    if app_configs is None:
        models = apps.get_models()
    else:
        models = chain.from_iterable(
            app_config.get_models() for app_config in app_configs
        )

    permission_model = apps.get_model("auth", "Permission")
    permission_name_max_length = permission_model._meta.get_field("name").max_length
    permission_codename_max_length = permission_model._meta.get_field("codename").max_length
    errors = []

    for model in models:
        opts = model._meta
        builtin_permissions = dict(_get_builtin_permissions(opts))
        errors.extend(check_builtin_permissions_length(
            opts, builtin_permissions, permission_name_max_length, permission_codename_max_length))
        errors.extend(check_custom_permissions(
            opts, builtin_permissions, permission_name_max_length, permission_codename_max_length))

    return errors

def check_builtin_permissions_length(opts, builtin_permissions, permission_name_max_length, permission_codename_max_length):
    errors = []
    max_builtin_permission_name_length = (
        max(len(name) for name in builtin_permissions.values())
        if builtin_permissions
        else 0
    )
    if max_builtin_permission_name_length > permission_name_max_length:
        verbose_name_max_length = permission_name_max_length - (
            max_builtin_permission_name_length - len(opts.verbose_name_raw)
        )
        errors.append(
            checks.Error(
                "The verbose_name of model '%s' must be at most %d "
                "characters for its builtin permission names to be at "
                "most %d characters."
                % (opts.label, verbose_name_max_length, permission_name_max_length),
                obj=opts.model,
                id="auth.E007",
            )
        )
    max_builtin_permission_codename_length = (
        max(len(codename) for codename in builtin_permissions.keys())
        if builtin_permissions
        else 0
    )
    if max_builtin_permission_codename_length > permission_codename_max_length:
        model_name_max_length = permission_codename_max_length - (
            max_builtin_permission_codename_length - len(opts.model_name)
        )
        errors.append(
            checks.Error(
                "The name of model '%s' must be at most %d characters "
                "for its builtin permission codenames to be at most %d "
                "characters."
                % (
                    opts.label,
                    model_name_max_length,
                    permission_codename_max_length,
                ),
                obj=opts.model,
                id="auth.E011",
            )
        )
    return errors

def check_custom_permissions(opts, builtin_permissions, permission_name_max_length, permission_codename_max_length):
    errors = []
    codenames = set()
    for codename, name in opts.permissions:
        if len(name) > permission_name_max_length:
            errors.append(
                checks.Error(
                    "The permission named '%s' of model '%s' is longer "
                    "than %d characters."
                    % (
                        name,
                        opts.label,
                        permission_name_max_length,
                    ),
                    obj=opts.model,
                    id="auth.E008",
                )
            )
        if len(codename) > permission_codename_max_length:
            errors.append(
                checks.Error(
                    "The permission codenamed '%s' of model '%s' is "
                    "longer than %d characters."
                    % (
                        codename,
                        opts.label,
                        permission_codename_max_length,
                    ),
                    obj=opts.model,
                    id="auth.E012",
                )
            )
        if codename in builtin_permissions:
            errors.append(
                checks.Error(
                    "The permission codenamed '%s' clashes with a builtin "
                    "permission for model '%s'." % (codename, opts.label),
                    obj=opts.model,
                    id="auth.E005",
                )
            )
        elif codename in codenames:
            errors.append(
                checks.Error(
                    "The permission codenamed '%s' is duplicated for "
                    "model '%s'." % (codename, opts.label),
                    obj=opts.model,
                    id="auth.E006",
                )
            )
        codenames.add(codename)
    return errors