import attr


@attr.s
class Settings(object):
    use_scope_checking = attr.ib(type=bool, default=False)
    ignore_dead_code = attr.ib(type=bool, default=True)
    ignore_equivalent_appends = attr.ib(type=bool, default=True)
    ignore_untyped_returns = attr.ib(type=bool, default=True)
    only_insert_executed_code = attr.ib(type=bool, default=True)
