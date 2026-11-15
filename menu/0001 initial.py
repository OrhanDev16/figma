import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=100, unique=True, verbose_name="Название"
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        blank=True,
                        max_length=120,
                        unique=True,
                        verbose_name="Слаг (для ссылки)",
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="categories/",
                        verbose_name="Картинка",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Порядок в меню"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, verbose_name="Показывать на сайте"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Создана"),
                ),
            ],
            options={
                "verbose_name": "Категория",
                "verbose_name_plural": "Категории",
                "ordering": ["order", "name"],
            },
        ),
        migrations.CreateModel(
            name="Dish",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150, verbose_name="Название")),
                (
                    "description",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Короткое описание"
                    ),
                ),
                ("ingredients", models.TextField(blank=True, verbose_name="Состав")),
                (
                    "allergens",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Аллергены"
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Цена, сом",
                    ),
                ),
                (
                    "weight",
                    models.PositiveIntegerField(default=0, verbose_name="Вес / объём"),
                ),
                (
                    "unit",
                    models.CharField(
                        choices=[("g", "г"), ("ml", "мл")],
                        default="g",
                        max_length=5,
                        verbose_name="Единица",
                    ),
                ),
                (
                    "calories",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Калорийность, ккал"
                    ),
                ),
                (
                    "cooking_time",
                    models.PositiveIntegerField(
                        default=15, verbose_name="Время приготовления, мин"
                    ),
                ),
                (
                    "kitchen_station",
                    models.CharField(
                        choices=[
                            ("hot", "Горячий цех"),
                            ("cold", "Холодный цех"),
                            ("pastry", "Кондитерский цех"),
                            ("bar", "Бар"),
                        ],
                        default="hot",
                        max_length=20,
                        verbose_name="Цех",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True, null=True, upload_to="dishes/", verbose_name="Фото"
                    ),
                ),
                ("is_new", models.BooleanField(default=False, verbose_name="Новинка")),
                ("is_hit", models.BooleanField(default=False, verbose_name="Хит")),
                (
                    "is_chef_choice",
                    models.BooleanField(default=False, verbose_name="Выбор шефа"),
                ),
                ("is_spicy", models.BooleanField(default=False, verbose_name="Острое")),
                (
                    "is_vegetarian",
                    models.BooleanField(default=False, verbose_name="Вегетарианское"),
                ),
                (
                    "is_featured",
                    models.BooleanField(
                        default=False, verbose_name="Показывать на главной"
                    ),
                ),
                (
                    "is_available",
                    models.BooleanField(default=True, verbose_name="В наличии"),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Порядок в категории"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Создано"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Изменено"),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dishes",
                        to="menu.category",
                        verbose_name="Категория",
                    ),
                ),
            ],
            options={
                "verbose_name": "Блюдо",
                "verbose_name_plural": "Блюда",
                "ordering": ["category__order", "order", "name"],
            },
        ),
    ]