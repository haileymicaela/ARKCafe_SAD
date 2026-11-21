from django.db import migrations


def copy_alert_recipients(apps, schema_editor):
    AlertRecipient = apps.get_model("administration", "AlertRecipient")
    Recipient = apps.get_model("core", "Recipient")
    database = schema_editor.connection.alias

    for alert_recipient in AlertRecipient.objects.using(database).all().iterator():
        Recipient.objects.using(database).create(
            name=alert_recipient.name,
            mobile_number=alert_recipient.mobile_number,
            department_id=alert_recipient.department_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_recipient_name"),
        ("administration", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_alert_recipients, migrations.RunPython.noop),
        migrations.DeleteModel(name="AlertRecipient"),
    ]
