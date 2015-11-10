import re
from lru import lru_cache_function

import requests
from flask import Flask, abort, render_template, request

import dateutil.parser

app = Flask(__name__)

EDITIONS_ENDPOINT = 'http://www.ascribe.io/api/editions/{}/'
PIECES_ENDPOINT = 'http://www.ascribe.io/api/pieces/{}/'


@lru_cache_function(max_size=1024, expiration=60 * 60)
def render(endpoint, item_id):

    # Examples of how to log errors, warnings, and debug info
    # app.logger.debug('A value for debugging')
    # app.logger.warning('A warning occurred (%d apples)', 42)
    # app.logger.error('An error occurred')

    user_agent = request.headers.get('User-Agent')
    app.logger.debug('User-Agent = {}'.format(user_agent))
    is_twitter = (user_agent[:7].lower() == 'twitter')

    if endpoint == 'editions':
        called_editions_endpoint = True
        endpoint_to_call = EDITIONS_ENDPOINT
    elif endpoint == 'pieces':
        called_editions_endpoint = False
        endpoint_to_call = PIECES_ENDPOINT
    else:
        app.logger.error("render() function was called with first " +
                         "argument not 'editions' or 'pieces'.")
        return

    # response is a dict representing the body of the HTTP response
    response = requests.get(endpoint_to_call.format(item_id)).json()

    if not response['success']:
        app.logger.debug("In response to HTTP GET " +
                         "/{}/{} , ".format(endpoint, item_id) +
                         "'success' == " +
                         "{}".format(response['success']))
        return

    # item_metadata is a dict with metadata about the edition or piece
    if called_editions_endpoint:
        item_metadata = response['edition']
    else:  # called pieces endpoint
        item_metadata = response['piece']

    # Contruct the description string

    desc = ''

    if is_twitter:
        desc += "by {}. ".format(item_metadata['artist_name'])
        # i.e. add the artist name to the description, since
        # Twitter doesn't use the meta author tag.

    # num_editions always exists, it's just -1 when a piece has no editions
    num_editions = item_metadata['num_editions']

    if called_editions_endpoint:
        desc += 'Edition {}/{}, '.format(item_metadata['edition_number'],
                                         num_editions)
    else:  # called pieces endpoint
        if int(num_editions) == -1:  # the piece has no editions
            desc += ''
        else:  # the piece has editions
            desc += '{} Editions, '.format(num_editions)

    year_created = item_metadata['date_created'][:4]

    desc += '{}, '.format(year_created)

    dt_registered_str = item_metadata['datetime_registered']
    # is an ISO 8601 string
    dt_registered = dateutil.parser.parse(dt_registered_str)
    # is a datetime.datetime object
    # which *should* have time zone already set to UTC
    time_str = '{:%-I:%M %p}'.format(dt_registered).lower()
    # looks like '9:42 pm'
    timezone = '{:%Z}'.format(dt_registered)
    # should be 'UTC' but will be the actual
    # time zone of dt_registered if it is not UTC
    date_str = '{:%B %-d, %Y}'.format(dt_registered)
    # looks like 'October 20, 2015'
    dt_str = '{} {} on {}'.format(time_str, timezone, date_str)

    desc += 'securely registered at {}. '.format(dt_str)
    desc += 'ascribe ID: {}'.format(item_metadata['bitcoin_id'])

    # Figure out what to send as the image URL

    mimetype = item_metadata['digital_work']['mime']
    # Potential values for mimetype (coming from ascribe, in item_metadata):
    # 'image', 'video', 'audio', others?

    # Set the image URL to the fallback image for starters
    img_url = 'https://s3-us-west-2.amazonaws.com/' + \
              'ascribe0/public/ascribe_circled_A_315x315.jpg'

    # but in some cases, replace it with a thumbnail image
    if mimetype in ['image', 'video']:
        if 'thumbnail' in item_metadata:
            if 'url_safe' in item_metadata['thumbnail']:
                img_url = item_metadata['thumbnail']['url_safe']
                # At the time of writing this code,
                # this thumbnail was "300 x 300" (bounding box)

            if 'thumbnail_sizes' in item_metadata['thumbnail']:
                tsizes = item_metadata['thumbnail']['thumbnail_sizes']
                if (tsizes is not None) and ('600x600' in tsizes):
                    img_url = tsizes['600x600']

    else:  # not an image or video, so there is no thumbnail image
        if is_twitter:
            img_url = None
            # i.e. send no image URLs, to conform to Twitter guidelines
            # "You should not use a generic image such as your website
            # logo, author photo, or other image that spans
            # multiple pages."

    # Future TODO optimization:
    # Determine the image height and width and populate meta tags such as
    # og:image:width
    # og:image:height
    # Maybe use pillow? It has many non-python dependencies...

    context = {
        'endpoint': endpoint,
        'item_id': item_id,
        'title': item_metadata['title'],
        'author': item_metadata['artist_name'],
        'description': desc,
        'img_url': img_url,
        'include_body': True,
        # etc.
    }

    # Determine if img_url points to a jpeg, gif, png, or other.
    # In the case of other, send no image MIME type info.
    # (Facebook only supports image/jpeg, image/gif and image/png )
    if img_url is not None:
        if img_url[-4:] == '.jpg' or img_url[-5:] == '.jpeg':
            context.update({'img_type': 'image/jpeg'})
        elif img_url[-4:] == '.gif':
            context.update({'img_type': 'image/gif'})
        elif img_url[-4:] == '.png':
            context.update({'img_type': 'image/png'})

    """
    # For now, we don't include og:video tags
    # because the video height and width are needed,
    # and we don't have them.

    # Videos have extra tags:
    if mimetype == 'video':
        encoding_urls = item_metadata['digital_work']['encoding_urls']
        for item in encoding_urls:
            # Zencoder creates mp4 and webm versions for us; get the mp4
            if item['label'] == 'mp4':
                # because Facebook only accepts Flash or mp4
                context.update({'video_url': item['url']})

        # TODO: Need to get video width and height.
        # The video width and height are not available in the API response.
        # Facebook says video width and height are *required*.
        # I checked to see what happens if you don't include them,
        # or make up values.
        # The result is a video that won't play embedded in Facebook.
        #
        # Question 1: How to *get* the video height and width?
        #
        # * Amazon S3 doesn't (currently) know the height or width of the
        #   videos we have stored there.
        # * Zencoder knows the height and width of the output video, so
        #   we can just ask Zencoder for those details. See:
        #   https://app.zencoder.com/docs/api/jobs/show
        #
        # Question 2: Where to store video height and width, going forward?
        #
        # * In our Postgres database? Available via the ascribe API somehow?
        # * In Amazon S3, as "metadata" associated with each video file?
        # * In the saved video file name (prepended or appended)?
        #   Note that we *already* append something to the end of filenames, in
        #   the case of duplicate filenames, so be careful!

        context.update({
            'video_width': ???,
            'video_height': ???
            })
    """

    full_html = render_template('final1.html', **context)
    # Remove all HTML comments
    full_html = re.sub("<!--.*?-->", "", full_html)
    # Remove all blank lines
    tmp = [s for s in full_html.splitlines(True) if s.strip("\r\n")]
    full_html = "".join(tmp)

    return full_html


@app.route('/app/<endpoint>/<item_id>')
def render_card(endpoint, item_id):
    # endpoint should be 'pieces' or 'editions'
    # item_id should be an integer or a hash
    if endpoint not in ['pieces', 'editions']:
        app.logger.error("cards can't handle /app/{}/{}".format(endpoint,
                         item_id))
        abort(404)
    page = render(endpoint, item_id)
    if not page:
        abort(404)
    return page


if __name__ == '__main__':
    # Note: In production, __name__ != '__main__'
    app.run(debug=True)
