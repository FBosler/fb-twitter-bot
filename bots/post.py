from collections import namedtuple
from bots.twitter_api import get_twitter_api
import random
import logging
from bots.config import get_post_data

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class MediumPost(namedtuple('MediumPost', ['id', 'url', 'tags', 'text'])):
    def make_post(self):
        used_tags = self.tags[:random.randint(1, len(self.tags))]
        return f'{self.text} {" ".join(["#" + tag for tag in used_tags])} {self.url}'

    def post_to_twitter(self):
        api = get_twitter_api()
        res = api.update_status(self.make_post())
        return res


def post_random_medium_article(event=None, context=None):
    posts = [MediumPost(*v) for k, v in get_post_data().items()]
    random_post = random.choice(posts)
    logger.info(f'Posting: {random_post}')
    random_post.post_to_twitter()


if __name__ == '__main__':
    #posts = [MediumPost(*v) for k, v in get_post_data().items()]
    #print(posts)
    post_random_medium_article()

