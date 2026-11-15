from django.db import migrations

CATEGORIES = [
    ('salaty', 'Салаты', 1),
    ('supy', 'Супы', 2),
    ('nacionalnaya-kuhnya', 'Национальная кухня', 3),
    ('goryachie-blyuda', 'Горячие блюда', 4),
    ('deserty', 'Десерты', 5),
    ('napitki', 'Напитки', 6),
]

DISHES = [
    {
        'category': 'salaty', 'name': 'Цезарь с курицей',
        'description': 'Классический салат с курицей гриль и соусом цезарь',
        'ingredients': 'Салат романо, куриное филе, гренки, пармезан, помидоры черри, соус цезарь',
        'allergens': 'gluten,milk,eggs,fish,mustard', 'price': 490, 'weight': 250, 'calories': 420,
        'station': 'cold', 'time': 10, 'badges': ['hit'], 'featured': True,
    },
    {
        'category': 'salaty', 'name': 'Греческий салат',
        'description': 'Свежие овощи с сыром фета и оливками',
        'ingredients': 'Огурцы, помидоры, болгарский перец, красный лук, оливки, фета, оливковое масло',
        'allergens': 'milk', 'price': 390, 'weight': 230, 'calories': 280,
        'station': 'cold', 'time': 8, 'badges': ['vegetarian'],
    },
    {
        'category': 'salaty', 'name': 'Ачичук',
        'description': 'Салат из помидоров с луком и острым перцем',
        'ingredients': 'Помидоры, репчатый лук, острый перец, зелень',
        'allergens': '', 'price': 220, 'weight': 200, 'calories': 90,
        'station': 'cold', 'time': 5, 'badges': ['vegetarian', 'spicy'],
    },
    {
        'category': 'supy', 'name': 'Шорпо',
        'description': 'Наваристый бульон из баранины с овощами',
        'ingredients': 'Баранина, картофель, морковь, лук, болгарский перец, зелень',
        'allergens': '', 'price': 420, 'weight': 400, 'calories': 380,
        'station': 'hot', 'time': 10, 'badges': [],
    },
    {
        'category': 'supy', 'name': 'Крем-суп из тыквы',
        'description': 'Нежный суп-пюре со сливками и тыквенными семечками',
        'ingredients': 'Тыква, сливки, лук, чеснок, тыквенные семечки',
        'allergens': 'milk', 'price': 360, 'weight': 300, 'calories': 260,
        'station': 'hot', 'time': 10, 'badges': ['new', 'vegetarian'],
    },
    {
        'category': 'supy', 'name': 'Том ям',
        'description': 'Острый тайский суп с креветками на кокосовом молоке',
        'ingredients': 'Креветки, кокосовое молоко, шампиньоны, лемонграсс, лайм, перец чили, рыбный соус',
        'allergens': 'seafood,fish', 'price': 590, 'weight': 350, 'calories': 310,
        'station': 'hot', 'time': 15, 'badges': ['new', 'spicy'],
    },
    {
        'category': 'nacionalnaya-kuhnya', 'name': 'Бешбармак',
        'description': 'Домашняя лапша с отварной кониной и бараниной',
        'ingredients': 'Конина, баранина, домашняя лапша, лук, бульон',
        'allergens': 'gluten,eggs', 'price': 690, 'weight': 450, 'calories': 780,
        'station': 'hot', 'time': 20, 'badges': ['hit', 'chef'], 'featured': True,
    },
    {
        'category': 'nacionalnaya-kuhnya', 'name': 'Лагман',
        'description': 'Тянутая лапша с говядиной и овощами',
        'ingredients': 'Говядина, лапша ручной тяжки, болгарский перец, редька, чеснок, помидоры',
        'allergens': 'gluten', 'price': 450, 'weight': 400, 'calories': 620,
        'station': 'hot', 'time': 15, 'badges': ['hit'], 'featured': True,
    },
    {
        'category': 'nacionalnaya-kuhnya', 'name': 'Манты',
        'description': 'Сочные манты с бараниной, 5 штук',
        'ingredients': 'Тесто, баранина, курдючный жир, лук, специи',
        'allergens': 'gluten', 'price': 420, 'weight': 350, 'calories': 640,
        'station': 'hot', 'time': 20, 'badges': [],
    },
    {
        'category': 'nacionalnaya-kuhnya', 'name': 'Плов чайханский',
        'description': 'Плов на казане с бараниной и жёлтой морковью',
        'ingredients': 'Рис девзира, баранина, жёлтая морковь, нут, чеснок, зира',
        'allergens': '', 'price': 480, 'weight': 350, 'calories': 690,
        'station': 'hot', 'time': 10, 'badges': ['chef'],
    },
    {
        'category': 'goryachie-blyuda', 'name': 'Стейк Рибай',
        'description': 'Мраморная говядина с овощами гриль',
        'ingredients': 'Говядина рибай, овощи гриль, соус демиглас',
        'allergens': '', 'price': 1650, 'weight': 350, 'calories': 820,
        'station': 'hot', 'time': 25, 'badges': ['chef'], 'featured': True,
    },
    {
        'category': 'goryachie-blyuda', 'name': 'Лосось на гриле',
        'description': 'Филе лосося с овощами и сливочным соусом',
        'ingredients': 'Лосось, брокколи, спаржа, сливочный соус, лимон',
        'allergens': 'fish,milk', 'price': 1290, 'weight': 300, 'calories': 540,
        'station': 'hot', 'time': 20, 'badges': ['new'], 'featured': True,
    },
    {
        'category': 'goryachie-blyuda', 'name': 'Куриные медальоны',
        'description': 'Куриное филе в сливочно-грибном соусе с картофельным пюре',
        'ingredients': 'Куриное филе, шампиньоны, сливки, картофельное пюре',
        'allergens': 'milk', 'price': 560, 'weight': 330, 'calories': 590,
        'station': 'hot', 'time': 20, 'badges': [],
    },
    {
        'category': 'deserty', 'name': 'Чизкейк Нью-Йорк',
        'description': 'Классический чизкейк с ягодным соусом',
        'ingredients': 'Сливочный сыр, песочное печенье, сливки, яйца, ягодный соус',
        'allergens': 'gluten,milk,eggs', 'price': 360, 'weight': 150, 'calories': 410,
        'station': 'pastry', 'time': 5, 'badges': ['hit'], 'featured': True,
    },
    {
        'category': 'deserty', 'name': 'Медовик',
        'description': 'Домашний медовый торт со сметанным кремом',
        'ingredients': 'Мёд, мука, сметана, яйца, сливочное масло',
        'allergens': 'gluten,milk,eggs', 'price': 320, 'weight': 150, 'calories': 450,
        'station': 'pastry', 'time': 5, 'badges': [],
    },
    {
        'category': 'deserty', 'name': 'Чак-чак',
        'description': 'Восточная сладость с мёдом',
        'ingredients': 'Мука, яйца, мёд, сахар',
        'allergens': 'gluten,eggs', 'price': 250, 'weight': 120, 'calories': 430,
        'station': 'pastry', 'time': 3, 'badges': [],
    },
    {
        'category': 'napitki', 'name': 'Чай с чабрецом',
        'description': 'Чёрный чай с чабрецом, чайник',
        'ingredients': 'Чёрный чай, чабрец',
        'allergens': '', 'price': 180, 'weight': 800, 'unit': 'ml', 'calories': 0,
        'station': 'bar', 'time': 5, 'badges': [],
    },
    {
        'category': 'napitki', 'name': 'Лимонад маракуйя',
        'description': 'Домашний лимонад с маракуйей и мятой',
        'ingredients': 'Маракуйя, лимон, мята, сахарный сироп, газированная вода',
        'allergens': '', 'price': 290, 'weight': 500, 'unit': 'ml', 'calories': 180,
        'station': 'bar', 'time': 5, 'badges': ['new'],
    },
    {
        'category': 'napitki', 'name': 'Капучино',
        'description': 'Эспрессо с молочной пенкой',
        'ingredients': 'Кофе арабика, молоко',
        'allergens': 'milk', 'price': 220, 'weight': 250, 'unit': 'ml', 'calories': 120,
        'station': 'bar', 'time': 5, 'badges': [],
    },
    {
        'category': 'napitki', 'name': 'Апельсиновый фреш',
        'description': 'Свежевыжатый апельсиновый сок',
        'ingredients': 'Апельсины',
        'allergens': '', 'price': 350, 'weight': 300, 'unit': 'ml', 'calories': 140,
        'station': 'bar', 'time': 5, 'badges': [], 'available': False,
    },
]

BADGE_FIELDS = {
    'new': 'is_new',
    'hit': 'is_hit',
    'chef': 'is_chef_choice',
    'spicy': 'is_spicy',
    'vegetarian': 'is_vegetarian',
}


def create_menu(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    Dish = apps.get_model('menu', 'Dish')

    categories = {}
    for slug, name, order in CATEGORIES:
        category, created = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'order': order})
        categories[slug] = category

    for number, item in enumerate(DISHES, start=1):
        fields = {
            'description': item['description'],
            'ingredients': item['ingredients'],
            'allergens': item['allergens'],
            'price': item['price'],
            'weight': item['weight'],
            'unit': item.get('unit', 'g'),
            'calories': item['calories'],
            'kitchen_station': item['station'],
            'cooking_time': item['time'],
            'is_featured': item.get('featured', False),
            'is_available': item.get('available', True),
            'order': number,
        }
        for badge in item['badges']:
            fields[BADGE_FIELDS[badge]] = True
        Dish.objects.get_or_create(category=categories[item['category']], name=item['name'], defaults=fields)


def delete_menu(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    Dish = apps.get_model('menu', 'Dish')
    Dish.objects.filter(name__in=[item['name'] for item in DISHES]).delete()
    Category.objects.filter(slug__in=[slug for slug, name, order in CATEGORIES], dishes__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_menu, delete_menu),
    ]