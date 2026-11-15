from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


ALLERGEN_CHOICES = (
    ('gluten', 'Глютен'),
    ('milk', 'Молоко'),
    ('eggs', 'Яйца'),
    ('nuts', 'Орехи'),
    ('peanuts', 'Арахис'),
    ('fish', 'Рыба'),
    ('seafood', 'Морепродукты'),
    ('soy', 'Соя'),
    ('sesame', 'Кунжут'),
    ('mustard', 'Горчица'),
    ('celery', 'Сельдерей'),
)
ALLERGEN_NAMES = dict(ALLERGEN_CHOICES)

BADGES = (
    ('new', 'is_new', 'Новинка'),
    ('hit', 'is_hit', 'Хит'),
    ('chef', 'is_chef_choice', 'Выбор шефа'),
    ('spicy', 'is_spicy', 'Острое'),
    ('vegetarian', 'is_vegetarian', 'Вегетарианское'),
)

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c',
    'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
    'я': 'ya', 'ң': 'n', 'ө': 'o', 'ү': 'u',
}


def make_slug(text):
    text = ''.join(TRANSLIT.get(letter, letter) for letter in text.lower())
    return slugify(text)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=120, unique=True, blank=True, verbose_name='Слаг (для ссылки)')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name='Картинка')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок в меню')
    is_active = models.BooleanField(default=True, verbose_name='Показывать на сайте')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # если слаг не указали - делаем из названия: "Салаты" -> "salaty"
        if not self.slug:
            base_slug = make_slug(self.name) or 'category'
            slug = base_slug
            number = 2
            while Category.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f'{base_slug}-{number}'
                number += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_available_dishes(self):
        return self.dishes.filter(is_available=True)


class Dish(models.Model):
    UNIT_CHOICES = (
        ('g', 'г'),
        ('ml', 'мл'),
    )
    STATION_CHOICES = (
        ('hot', 'Горячий цех'),
        ('cold', 'Холодный цех'),
        ('pastry', 'Кондитерский цех'),
        ('bar', 'Бар'),
    )

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='dishes', verbose_name='Категория')
    name = models.CharField(max_length=150, verbose_name='Название')
    description = models.CharField(max_length=255, blank=True, verbose_name='Короткое описание')
    ingredients = models.TextField(blank=True, verbose_name='Состав')
    allergens = models.CharField(max_length=255, blank=True, verbose_name='Аллергены')

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Цена, сом')
    weight = models.PositiveIntegerField(default=0, verbose_name='Вес / объём')
    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, default='g', verbose_name='Единица')
    calories = models.PositiveIntegerField(null=True, blank=True, verbose_name='Калорийность, ккал')
    cooking_time = models.PositiveIntegerField(default=15, verbose_name='Время приготовления, мин')
    kitchen_station = models.CharField(max_length=20, choices=STATION_CHOICES, default='hot', verbose_name='Цех')

    image = models.ImageField(upload_to='dishes/', blank=True, null=True, verbose_name='Фото')

    is_new = models.BooleanField(default=False, verbose_name='Новинка')
    is_hit = models.BooleanField(default=False, verbose_name='Хит')
    is_chef_choice = models.BooleanField(default=False, verbose_name='Выбор шефа')
    is_spicy = models.BooleanField(default=False, verbose_name='Острое')
    is_vegetarian = models.BooleanField(default=False, verbose_name='Вегетарианское')

    is_featured = models.BooleanField(default=False, verbose_name='Показывать на главной')
    is_available = models.BooleanField(default=True, verbose_name='В наличии')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок в категории')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Изменено')

    class Meta:
        ordering = ['category__order', 'order', 'name']
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Блюда'

    def __str__(self):
        return f'{self.name} - {self.price} сом'

    def get_allergens_list(self):
        if not self.allergens:
            return []
        return [code.strip() for code in self.allergens.split(',') if code.strip()]

    def set_allergens(self, codes):
        # сохраняем без повторов и в том же порядке, что в ALLERGEN_CHOICES
        codes = set(codes)
        self.allergens = ','.join(code for code, name in ALLERGEN_CHOICES if code in codes)

    def get_allergens_display(self):
        return [ALLERGEN_NAMES.get(code, code) for code in self.get_allergens_list()]

    @property
    def badges(self):
        result = []
        for code, field, label in BADGES:
            if getattr(self, field):
                result.append({'code': code, 'label': label})
        return result

    @property
    def weight_display(self):
        if not self.weight:
            return ''
        return f'{self.weight} {self.get_unit_display()}'

    def get_similar(self, limit=4):
        # другие блюда из этой же категории для блока "Вам может понравиться"
        return Dish.objects.filter(category=self.category, is_available=True).exclude(id=self.id)[:limit]