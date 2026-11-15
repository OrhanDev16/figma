from django.db import migrations

# 6 столов ресторана: (номер, мест, форма, X, Y, ширина, высота на плане 1000×600)
TABLES = [
    (1, 2, 'square', 120, 100, 100, 100),
    (2, 2, 'square', 450, 100, 100, 100),
    (3, 4, 'round', 780, 100, 120, 120),
    (4, 4, 'round', 120, 380, 120, 120),
    (5, 6, 'rectangle', 420, 380, 180, 110),
    (6, 8, 'rectangle', 740, 370, 200, 120),
]


def create_tables(apps, schema_editor):
    Table = apps.get_model('tables', 'Table')
    for number, seats, shape, x, y, width, height in TABLES:
        Table.objects.get_or_create(number=number, defaults={
            'seats': seats, 'shape': shape, 'pos_x': x, 'pos_y': y, 'width': width, 'height': height,
        })


def delete_tables(apps, schema_editor):
    Table = apps.get_model('tables', 'Table')
    Table.objects.filter(number__in=[t[0] for t in TABLES], reservations__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tables', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_tables, delete_tables),
    ]