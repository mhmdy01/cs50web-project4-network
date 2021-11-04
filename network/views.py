import json

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import User, Post


def index(request):
    posts = Post.objects.all()
    return render(request, "network/index.html", {
        'posts': posts,
    })

def profile(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404()
    
    user_posts = user.posts.all()
    return render(request, 'network/profile.html', {
        'user': user,
        'posts': user_posts
    })

def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            }, status=401)
    else:
        return render(request, "network/login.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")

def create_post(request):
    # validate the request first
    # ONLY AUTHENTICATED POST REQUESTS ALLOWED
    # TODO/future-issue: what about typical scenario of:
    # get/post @same route
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # start processing the request
    content = request.POST['content']
    p = Post.objects.create(content=content, user=request.user)

    return redirect(reverse('index'))

def edit_post(request, post_id):
    # reject non-authenticated requests (ie. user not logged-in)
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    # only accept PUT requests
    if request.method != 'PUT':
        return HttpResponseNotAllowed(['PUT'])

    # read post from db (and handle case of notfound)
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        raise Http404()

    # check if current user is post owner
    if request.user != post.user:
        return HttpResponse('Unauthorized', status=401)

    # load request data and replace post content with it
    data = json.loads(request.body)
    updated_content = data.get('content')
    post.content = updated_content
    post.save()
    
    # DON'T SEND WHOLE MODEL INSTANCE
    # cuz it requires more config to work (serialization... which isn't too straightforward)
    # return JsonResponse({'post': post})

    # instead send requird field (content after updating) for now
    # at the end, it's what all your frontend needs/uses
    return JsonResponse({'content': post.content})
