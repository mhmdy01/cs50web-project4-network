import json
from urllib.parse import urlparse

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import User, Post
from .utils import get_page

def index(request):
    posts = Post.objects.all()
    page_number = request.GET.get('page', 1)

    page = get_page(posts, page_number)
    if page is None:
        raise Http404()

    return render(request, "network/index.html", {
        'page': page,
    })

def profile(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404()

    user_posts = user.posts.all()
    page_number = request.GET.get('page', 1)

    page = get_page(user_posts, page_number)
    if page is None:
        raise Http404()

    # check if current user is already following the user whose profile is shown
    is_following = (
        request.user.is_authenticated
        and request.user.friends.filter(pk=user.id).exists()
    )
    # control when to show follow button
    can_follow = (
        request.user.is_authenticated
        and request.user != user
        and not is_following
    )
    # control when to show unfollow button
    can_unfollow = (
        request.user.is_authenticated
        and request.user != user
        and is_following
    )

    return render(request, 'network/profile.html', {
        'user': user,
        'page': page,
        'can_follow': can_follow,
        'can_unfollow': can_unfollow,
    })


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
    return HttpResponse(post.content)

def follow(request, username):
    # reject non-authenticated requests (ie. user not logged-in)
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    # only accept POST requests
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # read user to follow from db (and handle case of notfound)
    try:
        user_to_follow = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404()

    # users can't follow themselves
    if user_to_follow == request.user:
        return HttpResponseBadRequest("You can't follow yourself!")

    # users can't follow users they already follow!
    if request.user.friends.filter(pk=user_to_follow.id).exists():
        return HttpResponseBadRequest(f"You're already following {user_to_follow.username}")

    # when foo follows bar
    # bar is a friend to foo, foo is a follower to bar
    request.user.friends.add(user_to_follow)
    user_to_follow.followers.add(request.user)

    # redirect to user_to_follow profile
    return redirect(reverse('profile', kwargs={'username': username}))

def unfollow(request, username):
    # reject non-authenticated requests (ie. user not logged-in)
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    # only accept POST requests
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # read user_to_unfollow from db (and handle case of notfound)
    try:
        user_to_unfollow = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404()

    # users can't follow themselves
    if user_to_unfollow == request.user:
        return HttpResponseBadRequest("You can't unfollow yourself!")

    # users can't unfollow users they aren't friends with! (ie. aren't following)
    if not request.user.friends.filter(pk=user_to_unfollow.id).exists():
        return HttpResponseBadRequest(f"You can't unfollow {user_to_unfollow.username} as you aren't friends with them.")

    # when foo unfollows bar
    # bar is no longer a friend to foo, foo is no longer a follower to bar
    request.user.friends.remove(user_to_unfollow)
    user_to_unfollow.followers.remove(request.user)

    # redirect to user_to_unfollow profile
    return redirect(reverse('profile', kwargs={'username': username}))

def friends_posts(request):
    """View posts created by current user friends"""
    # only available for logged-in users
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    # find posts whose owners have current user as a follower
    posts = Post.objects.filter(user__followers=request.user)
    page_number = request.GET.get('page', 1)

    page = get_page(posts, page_number)
    if page is None:
        raise Http404()

    return render(request, 'network/following.html', {
        'page': page,
    })

def like_post(request, post_id):
    # reject non-authenticated requests (ie. user not logged-in)
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    # only accept POST requests
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # read post from db (and handle case of notfound)
    try:
        post_to_like = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        raise Http404()

    # check if current user already liked the post
    # because user can't like a post twice!
    if request.user.likes.filter(pk=post_to_like.id).exists():
        return HttpResponseBadRequest("You already liked that post.")

    # update post likes
    request.user.likes.add(post_to_like)

    # send updated likes and correct button (like/unlike)
    return render(request, 'network/likes.html', {
        'post': post_to_like,
    })

def unlike_post(request, post_id):
    # reject non-authenticated requests (ie. user not logged-in)
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    # only accept POST requests
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # read post from db (and handle case of notfound)
    try:
        post_to_unlike = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        raise Http404()

    # check if current user already liked the post
    # because user can't unlike a post they hadn't liked yet!
    if not request.user.likes.filter(pk=post_to_unlike.id).exists():
        return HttpResponseBadRequest("You hadn't liked that post yet.")

    # update post likes
    request.user.likes.remove(post_to_unlike)

    # send updated likes and correct button (like/unlike)
    return render(request, 'network/likes.html', {
        'post': post_to_unlike,
    })
