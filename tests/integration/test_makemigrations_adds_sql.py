import os
import re

import django.test
import pytest
from django.core.management import call_command
from freezegun import freeze_time

from tests.helpers import cleanup_migrations


def snapshot_transformer(content):
    lines = content.splitlines()

    # ignore all header lines
    for header in [
        "# -*- coding:",
        "# Generated by Django",
        "from __future__ import unicode_literals",
    ]:
        lines = [l1 for l1 in lines if not l1.startswith(header)]

    # remove "initial = True" line
    lines = [l2 for l2 in lines if "initial = True" not in l2]

    # reorder "AutoField()" keyword arguments
    def _reorder_kwargs(line):
        if "AutoField(" in line:
            kwargs = re.search(r"AutoField\(([^\)]+)\)", line).groups(0)[0]
            sorted_kwargs = ", ".join(sorted(kwargs.split(", ")))
            line = line.replace(kwargs, sorted_kwargs)

        return line

    lines = map(_reorder_kwargs, lines)

    # remove some SQL comments for django < 1.9
    # django 1.8- didn't have comments on SQL instructions
    lines = [l3 for l3 in lines if l3]

    return "\n".join(lines)


class TestMakemigrationsAddsSql(django.test.TestCase):
    def tearDown(self):
        cleanup_migrations()

    @freeze_time("2017-12-01")
    def test_makemigrations_adds_a_migration_file(self):
        call_command("makemigrations", "example_app")
        assert os.path.isfile("tests/example_app/migrations/0001_initial.py")

        content = open("tests/example_app/migrations/0001_initial.py").read()
        content.should.match_snapshot(
            "migrations__0001_initial.py", snapshot_transformer
        )

    @django.test.override_settings(BETTER_MIGRATIONS={"ALLOW_ENGINES": ["postgresql"]})
    def test_allow_engines(self):
        with pytest.raises(
            Exception,
            match="You are not allowed to generate migrations files with the DB engine 'sqlite'. "
            "Please use an engine among the following list: postgresql",
        ):
            call_command("makemigrations", "example_app")
