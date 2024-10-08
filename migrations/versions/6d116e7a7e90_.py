"""empty message

Revision ID: 6d116e7a7e90
Revises: ae0c4967df25
Create Date: 2024-09-09 17:45:54.677810

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d116e7a7e90'
down_revision = 'ae0c4967df25'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('default', sa.Boolean(), nullable=True),
    sa.Column('permissions', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
    sa.UniqueConstraint('name', name=op.f('uq_roles_name'))
    )
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_roles_default'), ['default'], unique=False)

    op.create_table('posts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('subject', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('body_html', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_posts_author_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_posts'))
    )
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_posts_timestamp'), ['timestamp'], unique=False)

    op.create_table('post_recommend',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], name=op.f('fk_post_recommend_post_id_posts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_post_recommend_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'post_id', name=op.f('pk_post_recommend'))
    )
    op.create_table('replies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('body_html', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_replies_author_id_users')),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], name=op.f('fk_replies_post_id_posts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_replies'))
    )
    with op.batch_alter_table('replies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replies_timestamp'), ['timestamp'], unique=False)

    op.create_table('reply_recommend',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('reply_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['reply_id'], ['replies.id'], name=op.f('fk_reply_recommend_reply_id_replies'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reply_recommend_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'reply_id', name=op.f('pk_reply_recommend'))
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('name', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('location', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('about_me', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('member_since', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_seen', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('avatar_hash', sa.String(length=32), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_users_role_id_roles'), 'roles', ['role_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_users_role_id_roles'), type_='foreignkey')
        batch_op.drop_column('avatar_hash')
        batch_op.drop_column('last_seen')
        batch_op.drop_column('member_since')
        batch_op.drop_column('about_me')
        batch_op.drop_column('location')
        batch_op.drop_column('name')
        batch_op.drop_column('role_id')

    op.drop_table('reply_recommend')
    with op.batch_alter_table('replies', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_replies_timestamp'))

    op.drop_table('replies')
    op.drop_table('post_recommend')
    with op.batch_alter_table('posts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_posts_timestamp'))

    op.drop_table('posts')
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_roles_default'))

    op.drop_table('roles')
    # ### end Alembic commands ###
