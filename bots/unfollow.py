import bots.utils as _utils
from dateutil.parser import parse
from bots.twitter_api import get_twitter_api
import random
import logging
import time
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def unfollow(event=None, context=None):
    if random.random() > .23:
        logger.info(f'Doing nothing this time')
    else:
        following_history = _utils.get_s3_data('following.json')

        sorted_by_following_date = sorted(
            [elem for elem in following_history.items() if 'unfollowed_at' not in elem[1]],
            key=lambda x: parse(x[1]['followed_at'])
        )

        number_to_unfollow = random.randint(1, 3)
        for currently_following in sorted_by_following_date[:number_to_unfollow]:
            _id = currently_following[0]

            try:
                print(_id)
                get_twitter_api().destroy_friendship(_id)
                following_history[_id]['unfollowed_at'] = datetime.datetime.now().isoformat()
                logger.info(f'Unfollowing: {_id}')
            except Exception as e:
                logger.error(f'Unfollowing: {_id} did not work with error {e}')
            time.sleep(random.randint(2, 8))

        _utils.sync_s3_data(following_history)
