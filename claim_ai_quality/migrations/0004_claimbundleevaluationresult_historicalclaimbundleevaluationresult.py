# Generated by Django 3.0.14 on 2022-02-20 11:23

import core.datetimes.ad_datetime
import core.fields
import dirtyfields.dirtyfields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import jsonfallback.fields
import simple_history.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('claim', '0012_item_service_jsonExtField'),
        ('claim_ai_quality', '0003_misclassification_report_role_right'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalClaimBundleEvaluationResult',
            fields=[
                ('id', models.UUIDField(db_column='UUID', db_index=True, default=None, editable=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', jsonfallback.fields.FallbackJSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', null=True)),
                ('version', models.IntegerField(default=1)),
                ('evaluation_hash', models.CharField(db_index=True, default=uuid.uuid4, max_length=36)),
                ('status', models.IntegerField(choices=[(0, 'Idle'), (1, 'Started'), (2, 'Finished'), (-1, 'Failed')], default=0)),
                ('request_time', core.fields.DateTimeField(db_column='RequestTime', default=core.datetimes.ad_datetime.AdDatetime.now)),
                ('response_time', core.fields.DateTimeField(db_column='ResponseTime', null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('user_created', models.ForeignKey(blank=True, db_column='UserCreatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('user_updated', models.ForeignKey(blank=True, db_column='UserUpdatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical claim bundle evaluation result',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='ClaimBundleEvaluationResult',
            fields=[
                ('id', models.UUIDField(db_column='UUID', default=None, editable=False, primary_key=True, serialize=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', jsonfallback.fields.FallbackJSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', null=True)),
                ('version', models.IntegerField(default=1)),
                ('evaluation_hash', models.CharField(default=uuid.uuid4, max_length=36, unique=True)),
                ('status', models.IntegerField(choices=[(0, 'Idle'), (1, 'Started'), (2, 'Finished'), (-1, 'Failed')], default=0)),
                ('request_time', core.fields.DateTimeField(db_column='RequestTime', default=core.datetimes.ad_datetime.AdDatetime.now)),
                ('response_time', core.fields.DateTimeField(db_column='ResponseTime', null=True)),
                ('claims', models.ManyToManyField(to='claim.Claim')),
                ('user_created', models.ForeignKey(db_column='UserCreatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='claimbundleevaluationresult_user_created', to=settings.AUTH_USER_MODEL)),
                ('user_updated', models.ForeignKey(db_column='UserUpdatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='claimbundleevaluationresult_user_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, models.Model),
        ),
    ]