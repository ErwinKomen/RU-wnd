# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-08-08 09:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0002_lemma_gloss'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='lemma',
            options={'verbose_name_plural': "Lemma's"},
        ),
        migrations.AddField(
            model_name='dialect',
            name='toonbaar',
            field=models.BooleanField(default=True, verbose_name='Mag getoond worden'),
        ),
        migrations.AddField(
            model_name='lemma',
            name='toonbaar',
            field=models.BooleanField(default=True, verbose_name='Mag getoond worden'),
        ),
        migrations.AddField(
            model_name='trefwoord',
            name='toonbaar',
            field=models.BooleanField(default=True, verbose_name='Mag getoond worden'),
        ),
        migrations.AlterIndexTogether(
            name='aflevering',
            index_together=set([('deel', 'sectie', 'aflnum')]),
        ),
        migrations.AlterIndexTogether(
            name='dialect',
            index_together=set([('stad', 'code', 'nieuw')]),
        ),
        migrations.AlterIndexTogether(
            name='lemmadescr',
            index_together=set([('lemma', 'description')]),
        ),
        migrations.AlterIndexTogether(
            name='trefwoord',
            index_together=set([('woord', 'toelichting')]),
        ),
    ]
