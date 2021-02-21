from flask import Flask, render_template, url_for, session, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from datetime import datetime
import bcrypt
import os


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.secret_key = os.environ.get('SECRET_KEY', '12123124')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db
session_ = Session(app)
session_.app.session_interface.db.create_all()


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False, default=datetime.now())
    author_nickname = db.Column(db.String(50), db.ForeignKey('user.nickname'))
    commentaries = db.relationship('Commentary', backref=db.backref('post'))
    likes = db.relationship('Like', backref=db.backref('post'))
    

    def __init__(self, title, text, author_nickname):
        self.title = title
        self.text = text
        self.author_nickname = author_nickname

    def __repr__(self):
        return f'<Post {self.id}, {self.author_nickname}>'



class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    users = db.relationship('User', backref=db.backref('roles'))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<Role {self.id}, {self.name}>'
        


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role_name = db.Column(db.Integer, db.ForeignKey('role.name'))
    posts = db.relationship('Post', backref=db.backref('user'))
    likes = db.relationship('Like', backref=db.backref('user'))

    def __init__(self, nickname, name, password, role_name):
        self.nickname = nickname
        self.name = name
        self.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        self.role_name = role_name

    def __repr__(self):
        return f'<User {self.id}, {self.nickname}, {self.role_name}>'


class Commentary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False, default=datetime.now())
    author_nickname = db.Column(db.String(50), db.ForeignKey('user.nickname'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))

    def __init__(self, text, author_nickname, post_id):
        self.text = text
        self.author_nickname = author_nickname
        self.post_id = post_id

    def __repr__(self):
        return f"<Commentary {self.id}, {self.author_nickname}, {self.post_id}>"

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_nickname = db.Column(db.String(50), db.ForeignKey('user.nickname'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    
    def __init__(self, post_id, user_nickname):
        self.user_nickname = user_nickname
        self.post_id = post_id

    def __repr__(self):
        return f'<Like {self.post_id}, {self.user_nickname}>'


@app.route('/', methods=['GET'])
def home():
    if not session.get('is_authenticated', False):
        session['is_authenticated'] = False
    posts = Post.query.order_by(Post.datetime).all()
    posts.reverse()
    return render_template('home.html', posts=posts)


@app.route('/users/signin', methods=['GET', 'POST'])
def signin():
    if request.method == "POST":
        user = User.query.filter_by(nickname=request.form['nickname']).first()
        if user is not None and bcrypt.checkpw(request.form['password'].encode(), user.password):
            session['nickname'] = user.nickname
            session['role'] = user.role_name
            session['is_authenticated'] = True
            return redirect(url_for('home'))
        flash("Wrong username or password!")
    return render_template('auth/signin.html')


@app.route('/users/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        query = User.query.filter_by(nickname=request.form['nickname']).first()
        if query is None:
            role_name = 'User'
            user = User(request.form['nickname'], request.form['name'], request.form['password'], role_name)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('signin'))
        flash("User with this username already exists!")
    return render_template('auth/signup.html')

@app.route('/users/change_password/', methods=['GET', 'POST'])
def change_password():
    if session['is_authenticated']:
        if request.method == 'POST':
            query = User.query.filter_by(nickname=session['nickname'])
            user = query.first()
            if user is None or not bcrypt.checkpw(request.form['old_password'].encode(), user.password):
                flash('Wrong old password!')
                return redirect(url_for('change_password'))
            if request.form['old_password'] != request.form['password']:
                new_password = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt())
                query.update({'password': new_password})
                flash('Your password has been changed!')
                return redirect(url_for('home'))
            flash('You`ve entered your old password!')
            return redirect(url_for('change_password'))
        return render_template('auth/change_password.html')
    flash('You must authorize!')
    return redirect(url_for('signin'))

@app.route('/users/logout/')
def logout():
    session.pop('nickname', None)
    session.pop('role', None)
    session['is_authenticated'] = False
    return redirect(url_for('home'))


@app.route('/users/<string:nickname>', methods=['GET'])
def user_posts(nickname):
    posts = Post.query.filter_by(author_nickname=nickname).all()
    return render_template('users/user_posts.html', nickname=nickname, posts=posts)


@app.route('/post/create/', methods=['GET', 'POST'])
def post_create():
    if session['is_authenticated']:
        if request.method == "POST":
            author_nickname = session['nickname']
            post = Post(request.form['title'], request.form['text'], author_nickname)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('home'))
        return render_template('posts/post_create.html')
    flash('You must authorize!')
    return redirect(url_for('signin'))


@app.route('/post/<int:post_id>/edit/', methods=['GET', 'POST'])
def post_edit(post_id):
    query = Post.query.filter_by(id=post_id)
    post = query.first()
    if session['is_authenticated'] and session['nickname'] == post.author_nickname:
        if request.method == "POST":
            query.update({'title': request.form['title'], 'text': request.form['text']})
            return redirect(url_for('post_detail', post_id=post_id))
        return render_template('posts/post_edit.html', post=post)
    flash('You haven`t permissions to edit this post!')
    return redirect(url_for('signin'))


@app.route('/post/<int:post_id>/delete/', methods=['GET', 'POST'])
def post_delete(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if session['is_authenticated'] and (session['nickname'] == post.author_nickname or session['role'] == 'Admin'):
        if request.method == "POST":
            db.session.delete(post)
            db.session.commit()
            return redirect(url_for('home'))
        return render_template('posts/post_delete.html', post=post)
    flash('You haven`t permissions to delete this post!')
    return redirect(url_for('signin'))


@app.route('/post/<int:post_id>/')
def post_detail(post_id):
    post = Post.query.filter_by(id=post_id).first()
    comments = post.commentaries
    comments.reverse()
    if session['is_authenticated']:
        is_liked = Like.query.filter_by(user_nickname=session['nickname'], post_id = post_id).first() is not None
    else: 
        is_liked = False
    likes = len(post.likes)
    return render_template('posts/post_detail.html', post=post, comments=comments, likes=likes, is_liked=is_liked)


@app.route('/post/<int:post_id>/like', methods=['GET'])
def like(post_id):
    if session['is_authenticated']:
        like = Like(post_id, session['nickname'])
        db.session.add(like)
        db.session.commit()
        return redirect(url_for('post_detail', post_id=post_id))

@app.route('/post/<int:post_id>/unlike', methods=['GET'])
def unlike(post_id):
    if session['is_authenticated']:
        like = Like.query.filter_by(post_id=post_id, user_nickname=session['nickname']).first()
        db.session.delete(like)
        db.session.commit()
        return redirect(url_for('post_detail', post_id=post_id))


@app.route('/post/<int:post_id>/comment/create', methods=['POST'])
def comment_create(post_id):
    if session['is_authenticated']:
        comment = Commentary(request.form['comment-text'], session['nickname'], post_id)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('post_detail', post_id=post_id))

@app.route('/post/<int:post_id>/comment/<int:comment_id>/delete', methods=['GET'])
def comment_delete(post_id, comment_id):
    if session['is_authenticated']:
        comment = Commentary.query.filter_by(id=comment_id).first()
        db.session.delete(comment)
        db.session.commit()
        return redirect(url_for('post_detail', post_id=post_id))





if __name__ == '__main__':
    app.run('0.0.0.0')

    
    
