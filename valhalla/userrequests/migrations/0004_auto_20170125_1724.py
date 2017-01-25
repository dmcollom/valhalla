# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-25 17:24
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('proposals', '0003_auto_20161019_2107'),
        ('userrequests', '0003_auto_20170109_2315'),
    ]

    operations = [
        migrations.CreateModel(
            name='DraftUserRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('content', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='proposals.Proposal')),
            ],
            options={
                'ordering': ['-modified'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='draftuserrequest',
            unique_together=set([('author', 'proposal', 'title')]),
        ),
    ]
