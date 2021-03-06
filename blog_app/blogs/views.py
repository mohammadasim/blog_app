from django.contrib.postgres.search import TrigramSimilarity
from django.core.mail import send_mail
from django.db.models import Count
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from taggit.models import Tag

from .models import Post
from .forms import EmailPostForm, CommentForm, SearchForm


class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'post/list.html'
    model = Post

    def get_queryset(self):
        tag_slug = self.kwargs.get('tag_slug')
        if tag_slug:
            tag = get_object_or_404(Tag, slug=tag_slug)
            queryset = self.model.published.filter(tags__in=[tag])
            return queryset
        else:
            return super().get_queryset()


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                             slug=post,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    # list of active comments for this post
    comments = post.comments.filter(active=True)
    new_comment = None

    if request.method == 'POST':
        # A comment was posted
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()
    else:
        comment_form = CommentForm()
    post_tag_ids = Post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tag_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')). \
                        order_by('-same_tags', '-publish')[:4]
    return render(request,
                  'post/detail.html',
                  {'post': post,
                   'new_comment': new_comment,
                   'comments': comments,
                   'comment_form': comment_form,
                   'similar_posts': similar_posts
                   })


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(
                post.get_absolute_url()
            )
            subject = f'{cd["name"]} recommends you read ' \
                      f'{post.title}'
            message = f'Read {post.title} at {post_url}\n\n' \
                      f'{cd["name"]}\'s comments: {cd["comments"]}'
            send_mail(subject, message, 'admin@myblog.com', [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'post/share.html', {'form': form, 'post': post, 'sent': sent})


def post_list(request, tag_slug=None):
    """
    List posts with a specific tag
    :param request:
    :param tag_slug:
    :return:
    """
    object_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])
    paginator = Paginator(object_list, 3)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(request, 'post/list.html', {
        'page': page,
        'posts': posts,
        'tag': tag
    })


def post_search(request):
    """
    View to deal with text search
    :param request:
    :return:
    """
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.published.annotate(
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gte=0.1).order_by('-similarity')
    return render(request,
                  'post/search.html',
                  {
                      'form': form,
                      'query': query,
                      'results': results
                  }
                  )
