# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-09 08:37
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0004_auto_20180808_1229'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='description',
            index_together=set([('toelichting', 'bronnenlijst', 'boek')]),
        ),
    ]
