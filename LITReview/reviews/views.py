from itertools import chain

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import (ConnectionForm, CreateReviewForm, CreateTicketForm,
                    RegistrationForm, SubscriptionForm)
from .utils import (check_password_confirmation, delete_review,
                    delete_subscribtion, delete_ticket, get_all_reviews,
                    get_followed_users, get_followed_users_viewable_reviews,
                    get_followed_users_viewable_tickets, get_review_by_pk,
                    get_ticket_by_pk, get_user_by_id, get_user_by_name,
                    get_users_by_name, get_users_subscriber,
                    get_users_viewable_reviews, get_users_viewable_tickets,
                    save_review, save_subscribtion, save_ticket,
                    save_updated_review, save_updated_ticket, username_exists)


# Home page
def get_connection_data(request):
    '''View used to manage user's log in.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request:
        form = ConnectionForm(request.POST)
        # Check whether it's valid:
        if form.is_valid():
            user = authenticate(
                    username=form.cleaned_data['username'].lower(),
                    password=form.cleaned_data['password'])
            if user:
                login(request, user)
                # A backend authenticated the credentials
                return redirect('reviews:feed')
            else:
                form.add_error(
                    'username',
                    "Nom d'utilisateur ou mot de passe incorrect.")
    # If a GET (or any other method) we'll create a blank form
    else:
        form = ConnectionForm()
    return render(request, 'reviews/home_page.html', {'form': form})


# Registration page
def get_registration_data(request):
    '''View used to append new user.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request:
        form = RegistrationForm(request.POST)
        # Check whether it's valid:
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            username = username.lower()
            # If the username is not already used
            if not username_exists(username):
                # Check if the password has been correctly set twice
                if check_password_confirmation(form):
                    # This user could be append to DB.
                    user = User.objects.create_user(username, '', password)
                    # And we could log in it
                    login(request, user)
                    return redirect('reviews:feed')
            else:
                # This username already exist,
                # we need to informed the user to choose another name.
                form.add_error(
                    'username',
                    f'Le nom d\'utilisateur "{username}" est d??j?? utilis??.')
                check_password_confirmation(form)
    # If a GET (or any other method) we'll create a blank form
    else:
        form = RegistrationForm()
    return render(request, 'reviews/registration.html', {'form': form})


# Feed page
@login_required(login_url='reviews:home_page')
def feed(request):
    '''View which manage the feed page.'''
    # Get queryset of reviews
    reviews = get_users_viewable_reviews(request.user)
    followed_users_reviews = get_followed_users_viewable_reviews(request.user)
    # Get queryset of tickets
    tickets = get_users_viewable_tickets(request.user)
    followers_tickets = get_followed_users_viewable_tickets(request.user)
    tickets = list(chain(tickets, followers_tickets))
    # Get all followed users
    followed_users = get_followed_users(request.user)
    # For each ticket, check if it has been reviewed by user
    for ticket in tickets:
        ticket.already_reviewed = False
        for review in get_all_reviews():
            if review.ticket == ticket:
                ticket.already_reviewed = True
                # Check also if this ticket has
                # been review by not followed user
                if (review.user not in followed_users and not review.user == request.user):
                    reviews = list(chain(reviews, get_review_by_pk(review.id)))
                break
    # Combine and sort the two types of posts
    posts = sorted(
        chain(reviews, tickets, followed_users_reviews, followers_tickets),
        key=lambda post: post.time_created,
        reverse=True
    )
    # Update context
    context = {}
    context['posts'] = posts
    # Check if there is message to display
    message_to_display = request.session.get('message_to_display')
    if message_to_display:
        if message_to_display == 'save_new_ticket':
            context['message'] = 'save_new_ticket'
        elif message_to_display == 'save_new_review':
            context['message'] = 'save_new_review'
        del request.session['message_to_display']
    return render(request, 'reviews/feed.html', context=context)


@login_required(login_url='reviews:home_page')
def create_review(request, ticket=None):
    '''View used to write a new review.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Create a form instance and
        # populate it with data from the request:
        form = CreateReviewForm(request.POST)
        # Check if this review if created from ticket's review
        if 'ticket_pk' in request.POST:
            pk = request.POST.get('ticket_pk')
            ticket = get_ticket_by_pk(pk)[0]
            # In order to removed "create review" button
            # in case of invalid form
            ticket.already_reviewed = True
            updated_data = request.POST.copy()
            updated_data.update({'title': ticket.title})
            updated_data.update({'description': ticket.description})
            updated_data.update({'image': ticket.image})
            form = CreateReviewForm(updated_data)
        # Check whether it's valid:
        if form.is_valid():
            save_review(request, form)
            # Ask to display a message
            request.session['message_to_display'] = 'save_new_review'
            return redirect('reviews:feed')
        else:
            return render(request, 'reviews/create_review.html', {'form': form})
    # If a GET (or any other method) we'll create a blank form
    else:
        # Check if this request come from a response to a ticket
        if 'ticket_pk' in request.GET:
            pk = request.GET.get('ticket_pk')
            ticket = get_ticket_by_pk(pk)[0]
            # In order to removed "create review" button
            # in case of invalid form
            ticket.already_reviewed = True
        # Create a form instance
        form = CreateReviewForm()
        # Update context
        context = {}
        context['form'] = form
        context['ticket'] = ticket
        return render(request, 'reviews/create_review.html', context=context)


@login_required(login_url='reviews:home_page')
def create_ticket(request):
    '''View used to ask for a review.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request:
        form = CreateTicketForm(request.POST)
        # Check whether it's valid:
        if form.is_valid():
            save_ticket(request, form)
            # Ask to display a message
            request.session['message_to_display'] = 'save_new_ticket'
            return redirect('reviews:feed')
    # If a GET (or any other method) we'll create a blank form
    else:
        form = CreateTicketForm()
    return render(request, 'reviews/create_ticket.html', {'form': form})


# Posts page
@login_required(login_url='reviews:home_page')
def posts(request):
    '''View which manage the posts page.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Check if its for delete ticket
        if request.POST.get('delete_ticket', None):
            # Delete ticket
            ticket = get_ticket_by_pk(request.POST.get('ticket_pk'))[0]
            title = ticket.title
            delete_ticket(ticket)
            # Ask to display a message
            request.session['message_to_display'] = (
                f'Votre ticket "{title}" a ??t?? supprim??.'
            )
        # Or if its for delete review
        elif 'delete_review' in request.POST:
            # Delete review
            review = get_review_by_pk(request.POST.get('review_pk'))[0]
            headline = review.headline
            delete_review(review)
            # Ask to display a message
            request.session['message_to_display'] = (
                f'Votre critique "{headline}" a ??t?? supprim??e.'
            )
        # Or if the request is to update ticket
        elif 'ticket_pk' in request.POST:
            pk = request.POST.get('ticket_pk')
            ticket = get_ticket_by_pk(pk)[0]
            # Create a form instance and
            # populate it with data from the request:
            updated_data = request.POST.copy()
            updated_data.update({'title': ticket.title})
            updated_data.update({'description': ticket.description})
            updated_data.update({'image_download': ticket.image})
            form = CreateTicketForm(updated_data)
            # Update context
            context = {}
            context['form'] = form
            context['ticket_pk'] = pk
            if bool(ticket.image):
                context['display_image'] = ticket.image.url
            return render(request, 'reviews/update_ticket.html', context=context)
        # Or if its to update review
        elif 'review_pk' in request.POST:
            pk = request.POST.get('review_pk')
            review = get_review_by_pk(pk)[0]
            # Create a form instance and
            # populate it with data from the request:
            updated_data = request.POST.copy()
            updated_data.update({'title': review.ticket.title})
            updated_data.update({'description': review.ticket.description})
            updated_data.update({'image_download': review.ticket.image})
            updated_data.update({'headline': review.headline})
            updated_data.update({'rating': review.rating})
            updated_data.update({'body': review.body})
            form = CreateReviewForm(updated_data)
            # Update context
            context = {}
            context['form'] = form
            context['review_pk'] = pk
            # Check if the review.ticket shall be update or only dispayed
            if not request.user == review.user:
                context['display_ticket'] = True
            return render(request, 'reviews/update_review.html', context=context)
        return redirect('reviews:posts')
    # If a GET (or any other method) we'll create the posts page
    else:
        # Get queryset of reviews
        reviews = get_users_viewable_reviews(request.user)
        # Get queryset of tickets
        tickets = get_users_viewable_tickets(request.user)
        # Combine and sort the two types of posts
        posts = sorted(
            chain(reviews, tickets),
            key=lambda post: post.time_created,
            reverse=True
        )
        # Update context
        context = {}
        context['posts'] = posts
        context['update'] = 'tickets_and_reviews'
        # Check if there is message to display
        message_to_display = request.session.get('message_to_display')
        if message_to_display:
            context['message_to_display'] = message_to_display
            del request.session['message_to_display']
        return render(request, 'reviews/posts.html', context=context)


@login_required(login_url='reviews:home_page')
def update_review(request, ticket=None):
    '''View used to write a new review.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Create a form instance and
        # populate it with data from the request:
        form = CreateReviewForm(request.POST)
        # Check if this review if created from ticket's review
        if 'ticket_pk' in request.POST:
            pk = request.POST.get('ticket_pk')
            ticket = get_ticket_by_pk(pk)[0]
            # In order to removed "create review" button
            # in case of invalid form
            ticket.already_reviewed = True
            updated_data = request.POST.copy()
            updated_data.update({'title': ticket.title})
            updated_data.update({'description': ticket.description})
            updated_data.update({'image': ticket.image})
            form = CreateReviewForm(updated_data)
        # Check whether it's valid:
        if form.is_valid():
            pk = request.POST.get('review_pk')
            review = get_review_by_pk(pk)[0]
            save_updated_review(request, form, review)
            # Ask to display a message
            request.session['message_to_display'] = (
                f'Votre critique "{review.headline}" a ??t?? modifi??.'
            )
            return redirect('reviews:posts')
    # If a GET (or any other method) we'll create a blank form
    else:
        # Check if this request come from a response to a ticket
        if 'ticket_pk' in request.GET:
            pk = request.GET.get('ticket_pk')
            ticket = get_ticket_by_pk(pk)[0]
            # In order to removed "create review" button
            # in case of invalid form
            ticket.already_reviewed = True
        # Create a form instance
        form = CreateReviewForm()
    # Update context
    context = {}
    context['form'] = form
    context['ticket'] = ticket
    return render(request, 'reviews/update_review.html', context=context)


@login_required(login_url='reviews:home_page')
def update_ticket(request):
    '''View used to ask for a review.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request:
        form = CreateTicketForm(request.POST)
        # Check whether it's valid:
        if form.is_valid():
            pk = request.POST.get('ticket_pk')
            ticket = get_ticket_by_pk(pk)[0]
            save_updated_ticket(request, form, ticket)
            # Ask to display a message
            request.session['message_to_display'] = (
                f'Votre ticket "{ticket.title}" a ??t?? modifi??.'
            )
            return redirect('reviews:posts')
    # If a GET (or any other method) we'll create a blank form
    else:
        form = CreateTicketForm(request.GET)
    return render(request, 'reviews/update_ticket.html', {'form': form})


# Subscription page
@login_required(login_url='reviews:home_page')
def subscription(request):
    '''View which managed the subscription page.'''
    # If this is a POST request we need to process the form data
    if request.method == 'POST':
        # Check if the request is a users research
        if request.POST.get('users_search'):
            users = get_users_by_name(request.POST.get('username', ''))
            print(users)
            # Removed all users already followed
            users_follows = get_followed_users(request.user)
            users_to_removed = []
            for user_follows in users_follows:
                for user in users:
                    if user_follows == user:
                        users_to_removed.append(user)
                        break
            for user in users_to_removed:
                users = users.exclude(username=user)
            if request.user in users:
                users = users.exclude(username=request.user)
            if get_user_by_name('Admin') in users:
                users = users.exclude(username='admin')
            # Create a form instance and
            # populate it with data from the request:
            form = SubscriptionForm(request.POST)
        # Or if its a subscribing request
        elif request.POST.get('subscribing'):
            user_follows = get_user_by_id(
                request.POST.get('subscribing'))
            save_subscribtion(
                request.user,
                user_follows[0])
            # Create a form instance
            form = SubscriptionForm()
            # Ask to display a message
            request.session['message_to_display'] = \
                f'Vous suivez ?? pr??sent {user_follows[0].username}.'
        # Or if its an unsubscribing request
        elif request.POST.get('unsubscribing'):
            user_follows = get_user_by_id(
                request.POST.get('unsubscribing'))
            delete_subscribtion(
                request.user,
                user_follows[0])
            # Create a form instance
            form = SubscriptionForm()
            # Ask to display a message
            request.session['message_to_display'] = \
                f'Vous ne suivez plus {user_follows[0].username}.'
        else:
            form = SubscriptionForm(request.POST)
    # If a GET (or any other method) we'll create a blank form
    else:
        # Create a form instance
        form = SubscriptionForm()
    # Returns queryset of subscribtions
    subscribtions = get_followed_users(request.user)
    # Returns queryset of subscribers
    subscribers = get_users_subscriber(request.user)
    # Update context
    context = {}
    context['form'] = form
    context['users_search'] = users if 'users' in locals() else None
    context['subscribtions'] = subscribtions
    context['subscribers'] = subscribers
    # Check if there is message to display
    message_to_display = request.session.get('message_to_display')
    if message_to_display:
        context['message_to_display'] = message_to_display
        del request.session['message_to_display']
    return render(request, 'reviews/subscription.html', context=context)


# Disconnection
def disconnect(request):
    '''Function used to log out the current user.'''
    logout(request)
    return redirect('reviews:home_page')
