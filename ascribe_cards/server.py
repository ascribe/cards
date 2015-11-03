import re
from lru import lru_cache_function

import requests
from flask import Flask, abort, render_template, url_for

import dateutil.parser

app = Flask(__name__)

EDITIONS_ENDPOINT = 'http://www.ascribe.io/api/editions/{}/'
PIECES_ENDPOINT = 'http://www.ascribe.io/api/pieces/{}/'


@lru_cache_function(max_size=1024, expiration=60 * 60)
def render(endpoint, item_id):
    if endpoint == 'editions':
        called_editions_endpoint = True
        endpoint_to_call = EDITIONS_ENDPOINT
    elif endpoint == 'pieces':
        called_editions_endpoint = False
        endpoint_to_call = PIECES_ENDPOINT
    else:
        return

    # response is a dict representing the body of the HTTP response
    response = requests.get(endpoint_to_call.format(item_id)).json()

    if not response['success']:
        return

    # item_metadata is a dict with metadata about the edition or piece
    if called_editions_endpoint:
        item_metadata = response['edition']
    else:  # called pieces endpoint
        item_metadata = response['piece']

    # Contruct the description string

    user_registered = item_metadata['user_registered']
    desc1 = 'Registered by ascribe user {} '.format(user_registered)

    dt_registered_str = item_metadata['datetime_registered']
    # is an ISO 8601 string
    dt_registered = dateutil.parser.parse(dt_registered_str)
    # is a datetime.datetime object
    desc2 = 'on {:%B %-d, %Y} (UTC).'.format(dt_registered)

    description = desc1 + desc2

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
        'description': description,
        'img_url': img_url,
        'include_body': True,
        # etc.
    }

    # Determine if img_url points to a jpeg, gif, png, or other.
    # In the case of other, send no image MIME type info.
    # (Facebook only supports image/jpeg, image/gif and image/png )
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


@app.route('/editions/<bitcoin_hash>')
def render_edition_card(bitcoin_hash):
    page = render('editions', bitcoin_hash)
    if not page:
        abort(404)
    return page


# The piece_id will be an integer like 1383
@app.route('/pieces/<int:piece_id>')
def render_piece_card(piece_id):
    page = render('pieces', piece_id)
    if not page:
        abort(404)
    return page


if __name__ == '__main__':
    # Note: In production, __name__ != '__main__'
    app.run(debug=True)
