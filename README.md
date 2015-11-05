# cards

A server to respond to Facebook's crawler, Twitter's crawler, etc. It's written using Flask.

## Why?

When someone shares an ascribe URL on Facebook, Facebook's crawler sends an HTTP request to that URL to get the Open Graph tags embedded in the page (e.g. title, description, image). It uses the values in those tags to automatically construct a page preview on Facebook.

Similar things are done by Twitter and other sites.

If you "view source" of an ascribe piece detail page, you'll see that there's not much HTML there. That's because we use JavaScript to render the full HTML on the client.

Facebook, Twitter, and others don't render JavaScript, so we can't provide the Open Graph (and other) tags in the JavaScript-rendered HTML. We have to provide those tags in some other way.

## Our Solution: cards

**giano** checks the User Agent and if it's Facebook's crawler, Twitter's crawler, or similar, then it routes the request to **cards**.

If **giano** sees a request for `/app/pieces/<piece_id>`, it sends `/pieces/<piece_id>` to **cards**.

If **giano** sees a request for `/app/editions/<bitcoin_id>`, it sends `/editions/<bitcoin_id>` to **cards**.

**cards** uses the ascribe API to get the information about the piece or edition in question. It uses that information to construct a bare-bones HTML file containing just the tags wanted by Facebook et al. It sends that file as the response.

## Possible Future Optimizations

* Once the ascribe REST API makes the height and width of videos availble, send all og:video tags, so that Facebook can play videos embedded in the Facebook timeline. There is a JIRA issue to make the necessary changes to the ascribe REST API: [AD-1284](https://ascribe.atlassian.net/browse/AD-1284)

* If we ever come to know the creator/artist/author Facebook Profile URL, then we could send that in an article:author tag.

* If we ever come to know the creator/artist/author Twitter @UserName, then we could send that in an twitter:creator tag.

* Support for the Twitter Player Card type (for videos and audio)? May not be so easy, and it may make the description disappear from the Twitter timeline, which may not be such a good idea.

