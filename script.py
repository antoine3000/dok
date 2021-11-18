import os
import sys
import shutil
import traceback
from jinja2 import Template, Environment, FileSystemLoader, BaseLoader
import markdown
from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime
import yaml
import rcssmin
import sass
from feedgen.feed import FeedGenerator

CONTENT_DIR = 'content'
PUBLIC_DIR = 'public'
MEDIAS_DIR = 'public/medias'
ENV_DIR = Environment(loader=FileSystemLoader('dok/templates'))
IMG_MAX_WIDTH = 1400


# ------------------------------------------------
# Dok
# ------------------------------------------------

# Decoration
def line():
    print('⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓')


# Message
print('')
line()
print('DOK')
line()


# ------------------------------------------------
# Settings
# ------------------------------------------------


settings_file = 'settings.yml'

# Default settings
try:
    with open('dok/' + settings_file, 'r') as file:
        settings = yaml.load(file, Loader=yaml.SafeLoader)
except:
    print('Settings file is missing.')
    line()
    print('')
    sys.exit()

# User settings
if os.path.isfile(settings_file):
    with open(settings_file, 'r') as file:
        settings_user = yaml.load(file, Loader=yaml.SafeLoader)

settings.update(settings_user)


# ------------------------------------------------
# Data collection
# ------------------------------------------------


class Article:
    def __init__(self, path, markdown, childs):
        self.path = path
        self.name = os.path.basename(os.path.normpath(path))
        self.slug, self.publication_date = self.get_info_from_path(self.path)
        self.markdown = markdown
        self.childs = childs
        self.childs_slug = self.get_childs_slug()
        self.metadata, self.content, self.toc = self.get_content()
        self.process_metadata()
        self.parent = self.get_parent()
        self.updated_content = self.get_updated_content(self.content)

    def asdict(self):
        return {
            'path': self.path,
            'markdown': self.markdown,
            'childs': self.childs,
            'childs_slug': self.childs_slug,
            'slug': self.slug,
            'url': self.slug + '.html',
            'content': self.updated_content,
            'metadata': self.metadata,
            'featured': self.featured,
            'featured_image': self.featured_image,
            'featured_desc': self.featured_desc,
            'featured_price': self.featured_price,
            'tags': self.tags,
            'parent': self.parent,
            'parent_url': self.parent + '.html',
            'title': self.title,
            'translation': self.translation,
            'toc': self.toc,
            'publication_date': self.publication_date,
            'last_update': self.last_update,
            'type': self.type,
            'open': self.open,
            'draft': self.draft,
            'reverse_order': self.reverse_order,
            'no_interface': self.no_interface,
            'has_parent': self.has_parent,
            'backlinks_to': self.backlinks_to,
            'backlinks_from': self.backlinks_from
        }

    def __repr__(self):
        return self.name

    def get_info_from_path(self, path):
        # publication date
        try:
            publication_date = datetime.strptime(self.name[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            print('☹  "' + self.name + '" must be renamed to start with a date (DD-MM-YYYY-) ☹')
            sys.exit()
        # slug
        slug_text = self.name[11:] if len(self.name) > 11 else self.name
        slug = slug_text.strip()
        if not slug in slug_list:
            slug_list.append(slug)
        else:
            slug_index = slug_list.index(slug)
            print('☹  One of these "' + slug + '" must be renamed to have unique names ☹')
            print('- ' + str(self.path))
            print('- ' + str(articles_list[slug_index]))
            line()
            sys.exit()
        return slug, publication_date

    def get_parent(self):
        parent = os.path.relpath(os.path.abspath(os.path.join(current, os.pardir)))
        parent = slugify(parent)
        self.has_parent = False if parent == CONTENT_DIR else True
        return parent

    def get_childs_slug(self):
        childs_slug = []
        for child in self.childs:
            path = str(self) + '/' + str(child)
            slug = slugify(path)
            childs_slug.append(slug)
        return childs_slug

    def get_content(self):
        with open(self.path + '/' + self.markdown, 'r') as file:
            md = markdown.Markdown(extensions=['meta', 'tables', 'toc', 'admonition', 'fenced_code'])
            content = md.convert(file.read())
            metadata = md.Meta
            toc = md.toc
        return metadata, content, toc

    def process_metadata(self):
        metadata = self.metadata
        try:
            self.title = metadata['title'][0]
        except KeyError:
            self.title = self.slug
        try:
            self.open = eval(metadata['open'][0])
        except KeyError:
            self.open = False
        try:
            self.draft = eval(metadata['draft'][0])
        except KeyError:
            self.draft = False
        try:
            self.reverse_order = eval(metadata['reverse_order'][0])
        except KeyError:
            self.reverse_order = False
        try:
            self.no_interface = eval(metadata['no_interface'][0])
        except KeyError:
            self.no_interface = False
        try:
            self.last_update = datetime.strptime(metadata['last_update'][0], '%Y-%m-%d').strftime('%d/%m/%Y')
        except KeyError:
            self.last_update = self.publication_date
        try:
            self.featured = eval(metadata['featured'][0])
        except KeyError:
            self.featured = False
        try:
            self.featured_image = metadata['featured_image'][0]
        except KeyError:
            self.featured_image = ''
        try:
            self.featured_desc = metadata['featured_desc'][0]
        except KeyError:
            self.featured_desc = ''
        try:
            self.featured_price = metadata['featured_price'][0]
        except KeyError:
            self.featured_price = ''
        try:
            self.tags = metadata['tags'][0].split(', ')
        except KeyError:
            self.tags = []
        try:
            self.translation = eval(metadata['translation'][0])
        except KeyError:
            self.translation = False
        try:
            self.type = metadata['type'][0]
        except KeyError:
            self.type = ''

    def get_backlinks_to(self, content):
        soup = BeautifulSoup(content, 'lxml')
        links = soup.find_all('a')
        backlinks_to = []
        for link in links:
            if link['href'].startswith('button:'):
              link['href'] = link['href'][7:]
              link['class'] = link.get('class', []) + ['btn']
            if 'http' in str(link) or 'mailto:' in str(link):
                link['class'] = link.get('class', []) + ['external']
            else:
                backlinks_to.append(link.string)
                link['class'] = link.get('class', []) + ['internal']
        self.backlinks_to = backlinks_to
        return str(soup)

    def get_backlinks_from(self):
        backlinks_from = []
        for article in articles_list:
            if self.slug in article.backlinks_to:
                backlinks_from.append(article.slug)
        self.backlinks_from = backlinks_from

    def get_updated_content(self, content):
        updated_content = self.get_backlinks_to(content)
        return updated_content


# Medias process
if not os.path.exists(MEDIAS_DIR):
    os.makedirs(MEDIAS_DIR)


def media_process(origin, destination):
    if not os.path.isfile(destination):
        shutil.copy2(origin, destination)
        if destination.endswith(tuple(['jpg', 'jpeg', 'png', 'JPG', 'JPEG'])):
            img = Image.open(destination)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new(img.mode[:-1], img.size, '#f6f4f2')
                background.paste(img, img.split()[-1])
                img = background
            wpercent = (IMG_MAX_WIDTH/float(img.size[0]))
            hsize = int((float(img.size[1])*float(wpercent)))
            img = img.resize((IMG_MAX_WIDTH, hsize), Image.ANTIALIAS)
            img.save(destination)


def wrap(to_wrap, wrap_in):
    contents = to_wrap.replace_with(wrap_in)
    wrap_in.append(contents)


def slugify(path):
    path_clean = os.path.basename(os.path.normpath(path))
    slug_text = path_clean[11:] if len(path_clean) >= 11 else path_clean
    slug = slug_text.strip()
    return slug


def html_update(html, slug):
    video_tag = '<video controls preload="auto"><source type ="video/mp4" src ="medias/' + slug + '-'
    file_link = '<a target="_blank" class="link-file" href="medias/' + slug + '-'
    html = html.replace('<video><source src="', video_tag)
    html = html.replace('<p><video', '<video')
    html = html.replace('</video></p>', '</video>')
    html = html.replace('<table>', '<div class="table"><table>')
    html = html.replace('</table>', '</table></div>')
    html = html.replace('<a target="_blank" href="file:', file_link)
    html = html.replace('<p>TODO:', '<p class="todo">To do:')
    # html = html.replace('href="button:', 'class="btn" href="')
    # figure
    soup = BeautifulSoup(html, 'lxml')
    # Image slug if translation
    image_slug = article_slug
    try:
        parent = articles[slug]['parent']
        if articles[parent]['translation']:
            image_slug = parent
    except KeyError:
        pass
    for img_tag in soup.findAll('img'):
        caption = soup.new_tag('figcaption')
        caption.append(img_tag['alt'])
        img_tag.append(caption)
        img_tag['loading'] = 'lazy'
        fig_tag = soup.new_tag("figure")
        img_tag['src'] = 'medias/' + image_slug + '-' + img_tag['src']
        img_src = img_tag['src']
        if "large:" in img_src:
            fig_tag['class'] = 'lg'
            img_tag['src'] = img_src.replace('large:', '')
        elif "small:" in img_src:
            fig_tag['class'] = 'sm'
            img_tag['src'] = img_src.replace('small:', '')
        else:
            fig_tag['class'] = 'md'
        wrap(img_tag, fig_tag)
    
    for article_sub in soup.findAll(class_='article--sub'):
        # sub article figure
        article_sub_id = article_sub.get('id')
        for img_tag in article_sub.findAll('img'):
            img_tag['src'] = img_tag['src'].replace(slug, article_sub_id)
        # sub article video
        for video_tag in article_sub.findAll('video'):
            video_source = video_tag.find('source', type = 'video/mp4')
            video_source['src'] = video_source['src'].replace(slug, article_sub_id)
    # links with no class = external
    # for content in soup.findAll('section', {'class': 'article__content'}):
    #     for link in content.findAll('a', {'class': None}):
    #         link['class'] = 'external'
    #         link['target'] = '_blank'
    html = str(soup)
    html = html.replace('<p><figure', '<figure')
    html = html.replace('</img></figure></p>', '</figure>')
    html = html.replace('</img></figure>', '</figure>')
    html = html.replace('</figure></p>', '</figure>')
    return html


# Check if content folder is not empty
try:
    content = os.listdir(CONTENT_DIR)
except FileNotFoundError:
    print('There is no content')
    line()
    print('')
    sys.exit()

# Loop through every folder in content and add the objects to a list
articles_list = []
slug_list = []

for current, childs, files in os.walk(CONTENT_DIR):
    # Loop through every files in folder
    for file in files:
        if str(file) == '_index.md':
            # Save this folder as an article
            articles_list.append(Article(path=current, markdown=file, childs=childs))
        elif str(file) == '.DS_Store':
            os.remove(current + '/' + file)
        elif not os.path.isdir(file):
            item_slug = slugify(current)
            item_path = current + '/' + file
            media_path = MEDIAS_DIR + '/' + item_slug + '-' + file
            media_process(item_path, media_path)

# Convert some settings to markdown
settings_to_markdown = ['introduction', 'footer', 'topbar']
for setting in settings_to_markdown:
    settings[setting] = markdown.markdown(settings[setting])


# ------------------------------------------------
# Reorganization
# ------------------------------------------------

articles = {}
tags = {}

# Reorder main articles list
sorted_articles_list = sorted(articles_list, key=lambda x: x.name)

for article in sorted_articles_list:
    # Reorder childs slug list
    if article.childs:
        article.childs.sort(reverse=article.reverse_order)
        childs_slug_ordered = []
        for child in article.childs:
            childs_slug_ordered.append(slugify(child))
        article.childs_slug = childs_slug_ordered

    # Get backlinks from
    article.get_backlinks_from()
    # Create a dictionary from the previously generated list so that it can be accessed from anywhere
    articles.update({article.slug: article.asdict()})
    # Get tags
    for tag in article.tags:
        tag = tag.strip()
        if not tag in tags:
            tags[tag] = []
        tags[tag].append(article.asdict())


# ------------------------------------------------
# Site generation
# ------------------------------------------------

def get_template(template):
    if os.path.isfile('templates/' + template):
        template_file = open('templates/' + template, 'r').read()
    else:
        template_file = open('dok/templates/' + template, 'r').read()
    return template_file

pages_sum = 0

# Make directories if they don't exist
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)

# Clean the public folder
public_items = os.listdir(PUBLIC_DIR)
for item in public_items:
    if '.html' in item:
        os.remove(PUBLIC_DIR + '/' + item)
print(':: Public folder — cleaned')

# Generate index page
index_template = ENV_DIR.from_string(get_template('index.html'))
index_html = index_template.render(articles=articles, settings=settings)
with open('public/index.html', 'w') as file:
    file.write(index_html)
pages_sum += 1
print(':: Index page — created')

# Generate content page
content_template = ENV_DIR.from_string(get_template('content.html'))
content_html = content_template.render(articles=articles, settings=settings)
with open('public/content.html', 'w') as file:
    file.write(content_html)
pages_sum += 1
print(':: Content page — created')

# Generate article pages
article_template = ENV_DIR.from_string(get_template('article.html'))
shop_template = ENV_DIR.from_string(get_template('shop.html'))
shop_item_template = ENV_DIR.from_string(get_template('shop_item.html'))
articles_sum = 0
for article in articles:
    articles_sum += 1
    article_slug = articles[article]['slug']
    article_url = 'public/' + article_slug + '.html'
    if articles[article]['type'] == 'shop':
        article_html = shop_template.render(article=articles[article], articles=articles, settings=settings)
    elif articles[article]['type'] == 'shop_item':
        article_html = shop_item_template.render(article=articles[article], articles=articles, settings=settings)
    else:
        article_html = article_template.render(article=articles[article], articles=articles, settings=settings)
    article_html_updated = html_update(article_html, article_slug)
    with open(article_url, 'w') as file:
        file.write(article_html_updated)
print(':: Article pages — created (' + str(articles_sum) + ')')

# Generate tag pages
tag_template = ENV_DIR.from_string(get_template('tag.html'))
tags_sum = 0
for tag in tags:
    tags_sum += 1
    tag_url = 'public/tag-' + tag + '.html'
    tag_html = tag_template.render(
        title=tag, articles=tags[tag], settings=settings)
    with open(tag_url, 'w') as file:
        file.write(tag_html)

print(':: Tag pages — created (' + str(tags_sum) + ')')


# ------------------------------------------------
# Assets
# ------------------------------------------------


if not os.path.exists('assets'):
    SCSS_FILE = "dok/assets/css/main.scss"
else:
   SCSS_FILE = "assets/css/main.scss"

SCSS_MAP = {SCSS_FILE: "public/assets/main.css"}
CSS_MAP = {"public/assets/main.css": "public/assets/main.min.css"}
FONTS_PATH_DOK = 'dok/assets/fonts/'
FONTS_PATH_USER = 'assets/fonts/'
IMAGES_PATH= 'assets/images/'
FONTS_PUBLIC = 'public/assets/fonts/'
IMAGES_PUBLIC = 'public/assets/images/'
JS_PATH = "assets/js/"
JS_PUBLIC = "public/assets/js/"


def compile_scss(scss):
    for source, dest in scss.items():
        mode = 'a' if os.path.exists(dest) else 'w'
        with open(dest, "w") as outfile:
            outfile.write(sass.compile(filename=source))


def minify_css(css):
    for source, dest in css.items():
        with open(source, "r") as infile:
            with open(dest, "w") as outfile:
                outfile.write(rcssmin.cssmin(infile.read()))


# Create directories if they don't exist yet
if not os.path.exists(FONTS_PUBLIC):
    os.makedirs(FONTS_PUBLIC)
if not os.path.exists(IMAGES_PUBLIC):
    os.makedirs(IMAGES_PUBLIC)
if not os.path.exists(JS_PUBLIC):
    os.makedirs(JS_PUBLIC)

# Copy fonts to public
if os.path.isdir(FONTS_PATH_USER):
    fonts_path = FONTS_PATH_USER
else:
    fonts_path = FONTS_PATH_DOK

if os.path.isdir(fonts_path):
    fonts = os.listdir(fonts_path)
    for font_file in fonts:
        if not os.path.isfile(FONTS_PUBLIC + font_file):
            shutil.copy2(fonts_path + font_file, FONTS_PUBLIC + font_file)

# Copy images to public
if os.path.isdir(IMAGES_PATH):
    images = os.listdir(IMAGES_PATH)
    for image_file in images:
        if not os.path.isfile(IMAGES_PUBLIC + image_file):
            shutil.copy2(IMAGES_PATH + image_file, IMAGES_PUBLIC + image_file)

# Copy Js to public
if os.path.isdir(JS_PATH):
    js = os.listdir(JS_PATH)
    for js_file in js:
        shutil.copy2(JS_PATH + js_file, JS_PUBLIC + js_file)

# Compile, minimize css
if os.path.isfile(SCSS_FILE):
    compile_scss(SCSS_MAP)
    minify_css(CSS_MAP)
    print(":: CSS — compiled and minified")


# ------------------------------------------------
# RSS feed
# ------------------------------------------------

fg = FeedGenerator()
fg.title(settings['title'])
fg.author({'name': settings['title']})
fg.link(href=settings['main_url'], rel='alternate')
fg.subtitle(settings['description'])
fg.language(settings['language'])
rssfeed = fg.rss_str(pretty=True)

for article in articles:
    date = articles[article]["last_update"] if articles[article]["last_update"] else articles[article]["publication_date"]
    if not articles[article]["draft"] and articles[article]["content"]:
        fe = fg.add_entry()
        fe.title(articles[article]["title"])
        fe.link(href=settings['main_url'] + '/' + articles[article]["slug"] + '.html')
        fe.author({'name': settings['title']})
        fe.description(articles[article]["content"][:1800] + '...')
        fe.pubDate(datetime.strptime(date, '%d/%m/%Y').strftime('%a %b %d %H:%M:%S %Y') + ' +0200')
fg.rss_file('public/rss.xml')
print(":: RSS feed — updated")



# ------------------------------------------------
# End
# ------------------------------------------------

line()
pages_sum = pages_sum + articles_sum + tags_sum
print(':: Dok has ' + str(pages_sum) + ' pages')
line()
print('Copy/paste this path in your web browser to visit your freshly generated website:')
print(os.path.abspath('public/index.html'))
line()
