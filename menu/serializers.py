from rest_framework import serializers

from .models import ALLERGEN_CHOICES, ALLERGEN_NAMES, Category, Dish


class CategorySerializer(serializers.ModelSerializer):
    dishes_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'order', 'is_active', 'dishes_count']
        extra_kwargs = {'slug': {'required': False}}

    def get_dishes_count(self, obj):
        # если посчитали во view через annotate - берём оттуда, иначе считаем сами
        if hasattr(obj, 'available_count'):
            return obj.available_count
        return obj.get_available_dishes().count()

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Название категории слишком короткое.')
        return value


class DishListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    weight_display = serializers.CharField(read_only=True)
    badges = serializers.ListField(read_only=True)

    class Meta:
        model = Dish
        fields = ['id', 'name', 'description', 'price', 'weight', 'unit', 'weight_display', 'image',
                  'category', 'category_name', 'category_slug', 'badges', 'is_featured', 'is_available']


class DishDetailSerializer(DishListSerializer):
    allergens = serializers.SerializerMethodField()
    station_display = serializers.CharField(source='get_kitchen_station_display', read_only=True)
    similar = serializers.SerializerMethodField()

    class Meta(DishListSerializer.Meta):
        fields = DishListSerializer.Meta.fields + [
            'ingredients', 'allergens', 'calories', 'cooking_time',
            'kitchen_station', 'station_display', 'similar', 'created_at', 'updated_at',
        ]

    def get_allergens(self, obj):
        return [{'code': code, 'name': ALLERGEN_NAMES.get(code, code)} for code in obj.get_allergens_list()]

    def get_similar(self, obj):
        return DishListSerializer(obj.get_similar(), many=True, context=self.context).data


class DishWriteSerializer(serializers.ModelSerializer):
    allergens = serializers.ListField(
        child=serializers.ChoiceField(choices=ALLERGEN_CHOICES),
        required=False,
        help_text='Например: ["milk", "eggs"]',
    )

    class Meta:
        model = Dish
        fields = ['id', 'category', 'name', 'description', 'ingredients', 'allergens', 'price', 'weight',
                  'unit', 'calories', 'cooking_time', 'kitchen_station', 'image',
                  'is_new', 'is_hit', 'is_chef_choice', 'is_spicy', 'is_vegetarian',
                  'is_featured', 'is_available', 'order']

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Название блюда слишком короткое.')
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Цена должна быть больше нуля.')
        if value > 100000:
            raise serializers.ValidationError('Слишком большая цена.')
        return value

    def validate_cooking_time(self, value):
        if value < 1 or value > 240:
            raise serializers.ValidationError('Время приготовления от 1 до 240 минут.')
        return value

    def validate_image(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Фото не должно быть больше 5 МБ.')
        return value

    def validate(self, attrs):
        category = attrs.get('category') or (self.instance.category if self.instance else None)
        name = attrs.get('name') or (self.instance.name if self.instance else None)
        if category and name:
            other_dishes = Dish.objects.filter(category=category)
            if self.instance:
                other_dishes = other_dishes.exclude(id=self.instance.id)
            for other_name in other_dishes.values_list('name', flat=True):
                if other_name.lower() == name.lower():
                    raise serializers.ValidationError({'name': 'В этой категории уже есть блюдо с таким названием.'})
        return attrs

    def create(self, validated_data):
        allergens = validated_data.pop('allergens', [])
        dish = Dish(**validated_data)
        dish.set_allergens(allergens)
        dish.save()
        return dish

    def update(self, instance, validated_data):
        allergens = validated_data.pop('allergens', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if allergens is not None:
            instance.set_allergens(allergens)
        instance.save()
        return instance

    def to_representation(self, instance):
        return DishDetailSerializer(instance, context=self.context).data


class MenuCategorySerializer(serializers.ModelSerializer):
    dishes = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'dishes']

    def get_dishes(self, obj):
        dishes = [dish for dish in obj.dishes.all() if dish.is_available]
        return DishListSerializer(dishes, many=True, context=self.context).data