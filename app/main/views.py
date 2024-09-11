from flask import render_template, redirect, url_for, request, flash, \
    make_response
from flask_login import login_required, current_user
from flask.globals import current_app
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, \
    PostReplyForm, CommentForm
from .. import db
from ..models import Permission, User, Role, Post, Reply, Comment
from ..decorators import admin_required, permission_required

@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', type=str, default='')  

    show_followed = False
    query=None

    if search != '':        
        search_word = '%%{}%%'.format(search)

        print('search_word=', search_word)
        sub_query = db.session.query(Reply.post_id, Reply.body, User.username)\
            .join(User, Reply.author_id == User.id).subquery()
        query = Post.query\
            .join(User)\
            .outerjoin(sub_query, sub_query.c.post_id == Post.id)\
            .filter(Post.subject.ilike(search_word) |       # 글제목
                    Post.body.ilike(search_word) |          # 글내용
                    User.username.ilike(search_word) |      # 작성자
                    sub_query.c.body.ilike(search_word) |   # 답변내용
                    sub_query.c.username.ilike(search_word) # 답변작성자
                    )\
            .distinct()       


    else:        

        if current_user.is_authenticated:
                show_followed = bool(request.cookies.get('show_followed', ''))

        if show_followed:
            query = current_user.followed_posts
        else:
            query = Post.query

    if query is not None:
        pagination = query.order_by(Post.timestamp.desc()).paginate(
            page=page, 
            per_page=current_app.config['MYBLOG_POSTS_PER_PAGE'], 
            error_out=False
        )
    else:
            pagination = None

    posts = pagination.items if pagination else []

    from flask_wtf import FlaskForm
    class DeleteForm(FlaskForm):
        pass
    
    form = DeleteForm()

    return render_template('index.html', posts=posts, 
                           show_followed=show_followed, 
                           pagination=pagination, 
                           search=search, 
                           form=form)

#---- 회원 프로필 ----
@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()  
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
    page=page, per_page=current_app.config['MYBLOG_POSTS_PER_PAGE'], error_out=False)

    posts = pagination.items  
    from flask_wtf import FlaskForm
    class DeleteForm(FlaskForm):
        pass

    form = DeleteForm()  # 폼 생성
    return render_template('user.html', user=user, posts=posts, pagination=pagination)

# 회원 프로필 수정
# 회원은 자신의 프로필 수정할 수 있음
@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('프로필을 수정하였습니다.')
        return redirect(url_for('.user', username=current_user.username))

    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

# 관리자 프로필 수정
# 관리자는 자신뿐 아니라 회원들의 프로필 수정할 수 있음
@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('프로필을 수정하였습니다.')
        return redirect(url_for('.user', username=user.username))

    form.email.data = user.email
    form.username.data = user.username
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile_admin.html', form=form, user=user)

# 글쓰기
@main.route('/post_write', methods=['GET', 'POST'])
@login_required
def post_write():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            subject=form.subject.data, 
            body=form.body.data,
            author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('main.index'))    

    return render_template('post_write.html', form=form)

# 댓글쓰기
@main.route('/post_reply/<int:post_id>', methods=['GET', 'POST'])
def post_reply(post_id):
    form = PostReplyForm()
    post = Post.query.get_or_404(post_id)
    
    if form.validate_on_submit():
        reply = Reply(body=request.form["body"], author=current_user._get_current_object())
        post.replies.append(reply)
        db.session.commit()
        return redirect('{}#reply_{}'.format(url_for('main.post_reply', post_id=post_id), reply.id))

    # 게시물 목록으로 돌아가는 링크를 템플릿에 전달
    return render_template('post_reply.html', post=post, form=form, back_url=url_for('main.index'))

#-- 추천 ----
@main.route('/recommend_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def recommend_post(post_id):
    post = Post.query.get_or_404(post_id)

    # 현재 사용자가 이미 이 글을 추천했는지 확인
    if current_user in post.like:
        flash('이미 이 게시물을 추천하셨습니다.')
        return redirect(url_for('main.post_reply', post_id=post_id))

    # 본인의 글 추천 방지
    if current_user._get_current_object() == post.author:
        flash('본인이 작성한 글은 추천할 수 없습니다.')
    else:
        # 추천 추가
        post.like.append(current_user._get_current_object())
        db.session.commit()

    return redirect(url_for('main.post_reply', post_id=post_id))

@main.route('/recommend_reply/<int:reply_id>', methods=['GET', 'POST'])
@login_required
def recommend_reply(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if current_user._get_current_object() == reply.author:
        flash('본인이 작성한 글은 추천할수 없습니다')
    else:
        reply.like.append(current_user._get_current_object())
        db.session.commit()
    return redirect(url_for('main.post_reply', post_id=reply.post_id))

# ---- post comment -----
@main.route('/write_post_comment/<int:post_id>', methods=['GET', 'POST'])
@login_required
def write_post_comment(post_id):
    form = CommentForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, author=current_user._get_current_object())
        post.comments.append(comment)
        db.session.commit()
        #return redirect(url_for('question.detail', question_id=question_id))
        return redirect('{}#comment_{}'.format(
            url_for('main.post_reply', post_id=post_id), comment.id))

    return render_template('comment_write.html', form=form)

@main.route('/modify_post_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def modify_post_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user._get_current_object() != comment.author:
        flash('수정권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=comment.post.id))

    if request.method == 'POST':
        form = CommentForm()
        if form.validate_on_submit():
            form.populate_obj(comment)
            db.session.commit()
            #return redirect(url_for('question.detail', question_id=comment.question.id))
            return redirect('{}#comment_{}'.format(
                url_for('main.post_reply', post_id=comment.post.id), comment.id))
    else:
        form = CommentForm(obj=comment)

    return render_template('comment_write.html', form=form)

@main.route('/delete_post_comment/<int:comment_id>')
@login_required
def delete_post_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post.id
    if current_user._get_current_object() != comment.author:
        flash('삭제권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=post_id))

    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('main.post_reply', post_id=post_id))

# ---- reply comment ----
@main.route('/write_reply_comment/<int:reply_id>', methods=['GET', 'POST'])
@login_required
def write_reply_comment(reply_id):
    form = CommentForm()
    reply = Reply.query.get_or_404(reply_id)
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, author=current_user._get_current_object())
        reply.comments.append(comment)
        db.session.commit()
        #return redirect(url_for('question.detail', question_id=question_id))
        return redirect('{}#comment_{}'.format(
            url_for('main.post_reply', post_id=reply.post.id), comment.id))

    return render_template('comment_write.html', form=form)

@main.route('/modify_reply_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def modify_reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user._get_current_object() != comment.author:
        flash('수정권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=comment.post.id))

    if request.method == 'POST':
        form = CommentForm()
        if form.validate_on_submit():
            form.populate_obj(comment)
            db.session.commit()
            #return redirect(url_for('question.detail', question_id=comment.question.id))
            return redirect('{}#comment_{}'.format(
                url_for('main.post_reply', post_id=comment.post.id), comment.id))
    else:
        form = CommentForm(obj=comment)

    return render_template('comment_write.html', form=form)

@main.route('/delete_reply_comment/<int:comment_id>')
@login_required
def delete_reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post.id
    if current_user._get_current_object() != comment.author:
        flash('삭제권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=post_id))

    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('main.post_reply', post_id=post_id))

#---- cleaning ----
@main.route('/cleaning')
@login_required
@permission_required(Permission.CLEAN)
def cleaning():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['MYBLOG_COMMENTS_PER_PAGE'],error_out=False)
    comments = pagination.items
    return render_template('cleaning.html', comments=comments,
                pagination=pagination, page=page)

@main.route('/cleaning/enable/<int:id>')
@login_required
@permission_required(Permission.CLEAN)
def cleaning_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.cleaning',
                            page=request.args.get('page', 1, type=int)))


@main.route('/cleaning/disable/<int:id>')
@login_required
@permission_required(Permission.CLEAN)
def cleaning_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.cleaning',
                            page=request.args.get('page', 1, type=int)))

#---- 팔로우 ----
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('main.index'))

    if current_user.is_following(user):
        flash('이미 팔로우하고 있습니다.')
        return redirect(url_for('main.user', username=username))

    current_user.follow(user)
    db.session.commit()
    flash('지금부터 %s님을 팔로우합니다.' % username)
    return redirect(url_for('main.user', username=username))    

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))

    if not current_user.is_following(user):
        flash('팔로우하고 있지 않습니다.')
        return redirect(url_for('.user', username=username))

    current_user.unfollow(user)
    db.session.commit()
    flash('더 이상 %s님을 팔로우하지 않습니다.' % username)
    return redirect(url_for('.user', username=username))

@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))

    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['MYBLOG_FOLLOWERS_PER_PAGE'],error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp} for item in pagination.items]

    return render_template('followers.html', user=user, title="팔로워",
                endpoint='main.followers', pagination=pagination, follows=follows)

@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)

    pagination = user.followed.paginate(
        page, per_page=current_app.config['MYBLOG_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="팔로잉",
                           endpoint='main.followed_by', pagination=pagination,
                           follows=follows)

@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp

@main.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('이 게시물을 삭제할 권한이 없습니다.')
        return redirect(url_for('main.index'))

    db.session.delete(post)  # 게시물 삭제
    db.session.commit()  # 데이터베이스에 삭제 내용 반영
    flash('게시물이 삭제되었습니다.')
    return redirect(url_for('main.index'))

@main.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    print('post_id:',post_id)
    post = Post.query.get_or_404(post_id)
    
    if current_user != post.author and not current_user.is_administrator():
        flash('수정 권한이 없습니다.')
        return redirect(url_for('main.index'))

    form = PostForm(obj=post)
    if form.validate_on_submit():
        print("폼 데이터:", form.subject.data, form.body.data)  # 디버깅용
        post.subject = form.subject.data
        post.body = form.body.data
        db.session.commit()
        flash('게시글이 수정되었습니다.')
        return redirect(url_for('main.post_reply', post_id=post.id))

    # # 수정할 폼 데이터 초기화
    # form.subject.data = post.subject
    # form.body.data = post.body

    return render_template('edit_post.html', form=form, post=post)
