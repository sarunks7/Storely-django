from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem


# -------------------------------------------------
# Function to get or create a session-based cart id
# request.session.session_key -> unique id for each user
# -------------------------------------------------
def _cart_id(request):
    cart_id = request.session.session_key
    if not cart_id:
        request.session.create()      # create new session if not exists
        cart_id = request.session.session_key
    return cart_id


# -------------------------------------------------
# ADD PRODUCT TO CART
# product_id comes from URL
# Handles:
# 1. Product variations (color, size)
# 2. Same product + same variation → increase quantity
# 3. Same product + different variation → new cart item
# -------------------------------------------------
def add_cart(request, product_id):

    # Get product safely (404 if not found)
    product = get_object_or_404(Product, id=product_id)

    # This list will store selected variations from POST
    product_variation = []

    # If user submits variation form (POST request)
    if request.method == 'POST':
        for key, value in request.POST.items():
            # key = color / size
            # value = red / M
            try:
                variation = Variation.objects.get(
                    variation_category__iexact=key,
                    variation_value__iexact=value
                )
                product_variation.append(variation)
            except:
                pass   # ignore if variation not found

    # Get existing cart OR create new cart using session id
    cart, created = Cart.objects.get_or_create(
        cart_id=_cart_id(request)
    )

    # Check if product already exists in cart
    cart_items = CartItem.objects.filter(product=product, cart=cart)

    if cart_items.exists():

        # ex_var_list → variations already in DB
        # id_list → cart item ids
        ex_var_list = []
        id_list = []

        for item in cart_items:
            existing_variation = item.variations.all()
            ex_var_list.append(list(existing_variation))
            id_list.append(item.id)

        # If same variation exists → increase quantity
        if product_variation in ex_var_list:
            index = ex_var_list.index(product_variation)
            item_id = id_list[index]

            item = CartItem.objects.get(id=item_id)
            item.quantity += 1
            item.save()

        # Else create new cart item for different variation
        else:
            item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart,
            )
            if product_variation:
                item.variations.add(*product_variation)
            item.save()

    # If product not in cart at all
    else:
        item = CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
        )
        if product_variation:
            item.variations.add(*product_variation)
        item.save()

    return redirect('cart')


# -------------------------------------------------
# DECREASE PRODUCT QUANTITY BY 1
# If quantity becomes 0 → delete item
# -------------------------------------------------
def remove_cart(request, product_id,cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(cart_id=_cart_id(request))
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
         cart_item.delete()
    except:
        pass
    return redirect('cart')


# -------------------------------------------------
# REMOVE PRODUCT COMPLETELY FROM CART
# -------------------------------------------------
def remove_cart_item(request, product_id,cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_item = CartItem.objects.get(product=product, cart=cart,id=cart_item_id)
    cart_item.delete()
    return redirect('cart')


# -------------------------------------------------
# DISPLAY CART PAGE
# Calculates:
# total price
# total quantity
# tax
# grand total
# -------------------------------------------------
def cart(request):

    total = 0
    quantity = 0
    tax = 0
    grand_total = 0
    cart_items = []

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        # Calculate total and quantity
        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity

        # 5% tax calculation
        tax = (5 * total) / 100
        grand_total = total + tax

    except Cart.DoesNotExist:
        pass   # cart not created yet

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }

    return render(request, 'store/cart.html', context)
