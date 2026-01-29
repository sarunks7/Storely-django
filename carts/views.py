from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.contrib.auth.decorators import login_required



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
    # Get current user
    current_user = request.user

    # Get product safely (404 if not found)
    product = Product.objects.get(id=product_id)

    # If user is authenticated, use their cart items
    if current_user.is_authenticated:
        product_variation = []
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]
                try:
                    variation = Variation.objects.get(variation_category__iexact=key,variation_value__iexact=value)
                    product_variation.append(variation)
                except:
                    pass

        # Check if cart item with same product and variations exists
        is_cart_item_exists = CartItem.objects.filter(product=product,user=current_user).exists()

        if is_cart_item_exists:
            cart_item = CartItem.objects.filter(product=product,user=current_user)
            # ex_var_list → variations already in DB
            # id_list → cart item ids

            ex_var_list = []
            id_list = []

            for item in cart_item:
                existing_variation = item.variations.all()
                ex_var_list.append(list(existing_variation))
                id_list.append(item.id)

            if product_variation in ex_var_list:
                index = ex_var_list.index(product_variation)
                item_id = id_list[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()
            else:
                item = CartItem.objects.create(product=product,quantity=1,user=current_user)
            
                if len(product_variation)>0:
                    item.variations.clear()
                    item.variations.add(*product_variation)
                item.save()
        else:
            item = CartItem.objects.create(
                product=product,
                quantity=1,
                user=current_user
            )
            if len(product_variation)>0:
                    item.variations.clear()
                    item.variations.add(*product_variation)
            item.save()
            

        return redirect('cart')
    
# user is not authenticated
# else block is for anonymous users

    else:
        # This list will store selected variations from POST
        product_variation = []

        # If user submits variation form (POST request)
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]
                # key = color / size
                # value = red / M
                try:
                    variation = Variation.objects.get(variation_category__iexact=key,variation_value__iexact=value)
                    product_variation.append(variation)
                except:
                    pass   # ignore if variation not found

        try:
            # Get cart using the cart_id present in the session
            cart = Cart.objects.get(cart_id=_cart_id(request))

        except Cart.DoesNotExist:
            # Create a new cart if not present
            cart = Cart.objects.create(
                cart_id=_cart_id(request)
            )
        cart.save()

        # Check if cart item with same product exists
        is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()

        if is_cart_item_exists:
            cart_item = CartItem.objects.filter(product=product, cart=cart)
            # ex_var_list → variations already in DB
            # id_list → cart item ids

            ex_var_list = []
            id_list = []

            for item in cart_item:
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
                if len(product_variation) > 0:
                    item.variations.clear()
                    item.variations.add(*product_variation)

        # If product not in cart at all, create new cart item
        else:
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart,
            )
            if len(product_variation) > 0:
                cart_item.variations.clear()
                cart_item.variations.add(*product_variation)
            cart_item.save()

        return redirect('cart')



# -------------------------------------------------
# DECREASE PRODUCT QUANTITY BY 1
# If quantity becomes 0 → delete item
# -------------------------------------------------
def remove_cart(request, product_id,cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
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
def remove_cart_item(request,product_id,cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user,id=cart_item_id)
    else:
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
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)

        else:
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


# -------------------------------------------------
# DISPLAY CHECKOUT PAGE
@login_required(login_url='login')
def checkout(request,total=0, quantity=0,cart_items=None):
    try:
        tax = 0
        grand_total = 0
        
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)

        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity
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
    return render(request, 'store/checkout.html', context)
# -------------------------------------------------
# Calculates:
# total price
# total quantity    
# tax
# grand total
# -------------------------------------------------
