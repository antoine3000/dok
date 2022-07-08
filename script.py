#!/usr/bin/python

import os
import sys
import shutil
import traceback
from jinja2 import Environment, FileSystemLoader
import markdown
from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime
import yaml
import rcssmin
import sass

CONTENT_DIR = 'content'
PUBLIC_DIR = 'public'
MEDIAS_DIR = 'public/medias'
TEMPLATES_DIR = "dok/templates"
ENV_DIR = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
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
            'featured_image': self.featured_image,
            'action': self.action,
            'template': self.template,
            'tags': self.tags,
            'parent': self.parent,
            'parent_url': self.parent + '.html',
            'title': self.title,
            'toc': self.toc,
            'publication_date': self.publication_date,
            'last_update': self.last_update,
            'open': self.open,
            'content_first': self.content_first,
            'reverse_order': self.reverse_order,
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
        slug = self.name[11:] if len(self.name) > 11 else self.name
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
            self.content_first = eval(metadata['content_first'][0])
        except KeyError:
            self.content_first = False
        try:
            self.reverse_order = eval(metadata['reverse_order'][0])
        except KeyError:
            self.reverse_order = False
        try:
            self.last_update = datetime.strptime(metadata['last_update'][0], '%Y-%m-%d').strftime('%d/%m/%Y')
        except KeyError:
            self.last_update = self.publication_date
        try:
            self.featured_image = metadata['featured_image'][0]
        except KeyError:
            self.featured_image = ''
        try:
            self.action = metadata['action'][0]
        except KeyError:
            self.action = ''
        try:
            self.template = metadata['template'][0]
        except KeyError:
            self.template = 'article'
        try:
            self.tags = metadata['tags'][0].split(', ')
        except KeyError:
            self.tags = []

    def get_backlinks_to(self, content):
        backlinks_to = []
        html = content.replace('[[', '<span class="backlink">').replace(']]', '</span>')
        soup = BeautifulSoup(html, 'lxml')
        backlinks = soup.find_all(class_='backlink')
        for backlink in backlinks:
            # Add it to a list of backlinks
            backlinks_to.append(backlink.string)
            # Replace the span by a link
            link_tag = soup.new_tag('a')
            link_tag['class'] = 'internal'
            link_tag['href'] = backlink.string + '.html'
            link_tag.string = backlink.text
            backlink.replaceWith(link_tag)
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


# Convert links
def convert_links(content):
    html = content.replace('[[', '<span class="link">').replace(']]', '</span>')
    soup = BeautifulSoup(html, 'lxml')
    links = soup.find_all(class_='link')
    for link in links:
        link_tag = soup.new_tag('a')
        link_tag['href'] = link.string + '.html'
        link_tag.string = link.text
        link.replaceWith(link_tag)
    return str(soup)


# Medias process
if not os.path.exists(MEDIAS_DIR):
    os.makedirs(MEDIAS_DIR)


def media_process(origin, destination):
    if not os.path.isfile(destination):
        shutil.copy2(origin, destination)
        if destination.endswith(tuple(['jpg', 'jpeg', 'png', 'JPG', 'JPEG'])):
            img = Image.open(destination)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new(img.mode[:-1], img.size, '#FFFFFF')
                background.paste(img, img.split()[-1])
                img = background
            wpercent = (IMG_MAX_WIDTH/float(img.size[0]))
            hsize = int((float(img.size[1])*float(wpercent)))
            img = img.resize((IMG_MAX_WIDTH, hsize), Image.Resampling.LANCZOS)
            img.save(destination)


def wrap(to_wrap, wrap_in):
    contents = to_wrap.replace_with(wrap_in)
    wrap_in.append(contents)


def slugify(path):
    slug = os.path.basename(os.path.normpath(path))[11:] if len(path) >= 11 else path
    return slug

def image_flux(image, slug):
    container = articles[slug]['metadata']['title']
    if (os.path.isfile('public/' + image)) and (not image in flux):
        flux[image] = {}
        flux[image]['image'] = image
        flux[image]['link'] = slug
        flux[image]['container'] = container


def html_update(html, slug):
    video_tag = '<video controls preload="auto"><source type ="video/mp4" src ="medias/' + slug + '-'
    html = html.replace('<video><source src="', video_tag)
    html = html.replace('<p><video', '<video')
    html = html.replace('</video></p>', '</video>')
    html = html.replace('<table>', '<div class="table"><table>')
    html = html.replace('</table>', '</table></div>')
    html = html.replace('<p>TODO:', '<p class="todo">To do:')
    html = html.replace('href="button:', 'class="btn" href="')
    # figure
    soup = BeautifulSoup(html, 'lxml')
    for img_tag in soup.findAll('img'):
        caption = soup.new_tag('figcaption')
        caption.append(img_tag['alt'])
        img_tag.append(caption)
        img_tag['loading'] = 'lazy'
        fig_tag = soup.new_tag("figure")
        img_tag['src'] = 'medias/' + article_slug + '-' + img_tag['src']
        img_src = img_tag['src']
        if "large:" in img_src:
            fig_tag['class'] = 'lg'
            img_tag['src'] = img_src.replace('large:', '')
        elif "small:" in img_src:
            fig_tag['class'] = 'sm'
            img_tag['src'] = img_src.replace('small:', '')
        else:
            fig_tag['class'] = 'md'
        if ":flux" in img_src:
            img_tag['src'] = img_tag['src'].replace(':flux', '')
            image_flux(str(img_tag['src']), slug)
        wrap(img_tag, fig_tag)
    # sub article figure
    for article_sub in soup.findAll(class_='article--sub'):
        article_sub_id = article_sub.get('id')
        for img_tag in article_sub.findAll('img'):
            img_tag['src'] = img_tag['src'].replace(slug, article_sub_id)
        # sub article video
        for video_tag in article_sub.findAll('video'):
            video_source = video_tag.find('source', type = 'video/mp4')
            video_source['src'] = video_source['src'].replace(slug, article_sub_id)
        # sub article link
        for article_file in article_sub.findAll('.link-file'):
            article_file['href'] = article_file['href'].replace('medias/' + slug, 'medias/' + article_sub_slug)
    # external links target blank
    # links with no class = external
    for content in soup.findAll('section', {'class': 'article__content'}):
        for link in content.findAll('a', {'class': None}):
            link['class'] = 'external'
            link['target'] = '_blank'
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
        elif not os.path.isdir(file):
            item_slug = slugify(current)
            item_path = current + '/' + file
            media_path = MEDIAS_DIR + '/' + item_slug + '-' + file
            media_process(item_path, media_path)

# Convert some settings to markdown
settings_to_markdown = ['introduction', 'footer']
for setting in settings_to_markdown:
    if setting in settings:
        setting_md = markdown.markdown(settings[setting])
        settings[setting] = convert_links(setting_md)


# ------------------------------------------------
# Reorganization
# ------------------------------------------------

articles = {}
tags = {}
flux = {}

# Reorder main articles list
sorted_articles_list = sorted(articles_list, key=lambda x: x.name)
sorted_articles_list.reverse()

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

index_sum, articles_sum = 0, 0
templates = os.listdir(TEMPLATES_DIR)

def get_template(template):
    if os.path.isfile('templates/' + template):
        template_file = open('templates/' + template, 'r').read()
    else:
        template_file = open('dok/templates/' + template, 'r').read()
    return template_file

# Make directories if they don't exist
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)

# Clean the public folder
public_items = os.listdir(PUBLIC_DIR)
for item in public_items:
    if '.html' in item:
        os.remove(PUBLIC_DIR + '/' + item)
print(':: Public folder — cleaned')

# Generate article pages
article_template = ENV_DIR.from_string(get_template('article.html'))
articles_sum = 0
for article in articles:
    article_meta_template = str(articles[article]['template'] + '.html')
    template = article_meta_template if article_meta_template in templates else 'article.html'
    article_template = ENV_DIR.get_template(template)
    article_slug = articles[article]['slug']
    article_url = 'public/' + article_slug + '.html'
    article_html = article_template.render(article=articles[article], articles=articles, settings=settings)
    article_html_updated = html_update(article_html, article_slug)
    with open(article_url, 'w') as file:
        file.write(article_html_updated)
    articles_sum += 1
print(':: Article pages — created (' + str(articles_sum) + ')')

# Generate tag pages
tag_template = ENV_DIR.from_string(get_template('tag.html'))
for tag in tags:
    tag_url = 'public/' + tag + '.html'
    tag_html = tag_template.render(
        title=tag, articles=tags[tag], settings=settings)
    with open(tag_url, 'w') as file:
        file.write(tag_html)
    index_sum += 1
print(':: Tag pages — created (' + str(index_sum) + ')')

# Generate index page
index_template = ENV_DIR.from_string(get_template('index.html'))
index_html = index_template.render(articles=articles, settings=settings)
with open('public/index.html', 'w') as file:
    file.write(index_html)
index_sum += 1
print(':: Index page — created')

# Generate content page
content_template = ENV_DIR.from_string(get_template('content.html'))
content_html = content_template.render(articles=articles, settings=settings)
with open('public/content.html', 'w') as file:
    file.write(content_html)
index_sum += 1
print(':: Content page — created')

# Generate Flux page
flux_metadata = [flux[item] for item in flux]
flux_template = ENV_DIR.from_string(get_template('flux.html'))
flux_html = flux_template.render(articles=flux_metadata, settings=settings)
flux_slug = settings['flux']['slug']
articles_sum += 1
with open('public/' + flux_slug + '.html', 'w') as file:
    file.write(flux_html)
print(':: Flux page — created')



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
FONTS_PUBLIC = 'public/assets/fonts/'


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


# Create fonts directory if it doesn't exist yet
if not os.path.exists(FONTS_PUBLIC):
    os.makedirs(FONTS_PUBLIC)

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

# Compile, minimize css
if os.path.isfile(SCSS_FILE):
    compile_scss(SCSS_MAP)
    minify_css(CSS_MAP)
    print(":: CSS — compiled and minified")


# ------------------------------------------------
# End
# ------------------------------------------------

pages_sum = index_sum + articles_sum
line()
print(':: Dok has ' + str(pages_sum) + ' pages')
line()
print('Copy/paste this path in your web browser to visit your freshly generated website:')
print(os.path.abspath('public/index.html'))
line()