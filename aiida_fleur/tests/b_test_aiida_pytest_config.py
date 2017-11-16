#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io

from aiida_pytest.contextmanagers import redirect_stdout


def test_configure_from_file(configure):
    from aiida.orm.user import User
    user = User.get_all_users()[0]
    assert user.first_name == 'AiiDA'


def test_db_flushed(configure):
    from aiida.orm.data.base import Str
    test_string = 'this string should not be present when the test run starts'
    tag = 'Test string tag'
    from aiida.orm.querybuilder import QueryBuilder
    qb = QueryBuilder()
    qb.append(Str, filters={'label': {'==': tag}})
    assert not qb.all()
    str_obj = Str(test_string)
    str_obj.label = tag
    str_obj.store()


def test_daemon_running(configure_with_daemon):
    from aiida.cmdline.verdilib import Daemon
    output = io.BytesIO()
    with redirect_stdout(output):
        Daemon().daemon_status()
    assert '## Found 1 process running:' in output.getvalue()