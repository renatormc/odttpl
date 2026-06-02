# ODTTPL


#### Render ODT reports with Jinja2


ODTTPL lets you use Open Document Text (ODT) files as templates for reports, letters, and other documents. Templates are composed visually in OpenOffice.org or LibreOffice Writer, then rendered with [Jinja2 template syntax][1].

Most Jinja2 features work inside ODT templates, including variable interpolation, filters, and control flow (conditionals, loops). The rendered output is a valid ODT document that can be converted to PDF, DOCX, or other formats using the UNO Bridge or a library like [PyODConverter][2].

## Installing

    pip install odttpl

## Rendering a Template
```python
    from odttpl import Renderer

    engine = Renderer()
    engine.render(template, dest="output.odt", context={"foo": foo, "bar": bar})
```

ODTTPL implements a class called `Renderer`. `Renderer` takes a single argument called `environment` which is a jinja **[Environment][3]**.

To render a template create an instance of class `Renderer` and call the instance's method `render` passing a template file, a destination path, and a context dictionary with template variables:

```python
    render(template: str | Path,
           dest: Path | str,
           context: dict,
           pos_process: bool = False,
           docid: str | None = None) -> None
```

- `template` — Path to the ODT template file.
- `dest` — Output path for the rendered ODT document.
- `context` — Dictionary of template variables.
- `pos_process` — If `True`, runs post-processing to replace sequence/cross-reference markers with real ODF XML (see *Post-Processing* below).
- `docid` — Optional document ID to embed in the document metadata.

The rendered document is written directly to `dest`. There is no return value.

Before rendering a template, you can configure the internal templating engine using the `Renderer` instance's variable `environment`, which is an instance of jinja2 **[Environment][3]** class. For example, to declare a custom filter use:
```python
    from odttpl import Renderer

    engine = Renderer()

    # Configure custom application filters
    engine.environment.filters['custom_filer'] = filter_function
    engine.render(template, dest="output.odt", context={"foo": foo, "bar": bar})
```

## Post-Processing

ODTTPL can post-process a rendered document to replace plain-text markers with proper ODF XML for auto-numbered sequences and cross-references. This feature was designed for invoices, proposals, and other documents that need numbered figures, tables, or sections.

Enable it by passing `pos_process=True` to `render()`:

```python
engine.render(template, dest="output.odt", context={...}, pos_process=True)
```

### Supported Markers

Type these markers directly into LibreOffice Writer (no special fields required):

| Marker | Example | Description |
|---|---|---|
| `@seq(Type, RefName)` | `@seq(Foto, ref1)` | Auto-incrementing sequence number |
| `@cross(RefName)` | `@cross(ref1)` | Cross-reference to a sequence by ref name |
| `${RefName}` | `${ref1}` | Shorthand for `@cross(RefName)` |

### How It Works

1. `@seq(Foto, ref1)` is replaced with a `<text:sequence>` element that auto-increments per type (`Foto`, `Figura`, etc.) and registers `ref1` as its reference name.
2. `@cross(ref1)` or `${ref1}` is replaced with a `<text:sequence-ref>` element showing the number of the referenced sequence.
3. Markers that span multiple styled spans (e.g., a bold word inside a marker) are normalized before replacement.

Because the markers are plain text, they survive template rendering untouched — the post-processor runs *after* Jinja2 has finished, ensuring sequence numbering is always final and accurate.

## Composing Templates

ODTTPL templates are simple ODT documents. You can create them using Writer. An OpenDocument file is basically a ZIP archive containing some XML files. If you plan to use control flow or conditionals it is a good idea to familiarise yourself a little bit with the OpenDocument XML to understand better what's going on behind the scenes.

### Printing Variables

Since ODTTPL use the same template syntax of Jinja2, to print a varible type a double curly braces enclosing the variable, like so:
```jinja
    {{ foo.bar }}
    {{ foo['bar'] }}
```

However, mixing template instructions and normal text into the template document may become confusing and clutter the layout and most important, in most cases will produce invalid ODT documents. ODTTPL recommends using an alternative way of inserting fields. Insert a visual field in LibreOffice Writer from the menu `Insert` > `Fields` > `Other...` (or just press `Ctrl+F2`), then click on the `Functions` tab and select `Input field`. Click `Insert`. A dialog will appear where you can insert the print instructions. You can even insert simple control flow tags to dynamically change what is printed in the field.

ODTTPL will handle multiline variable values replacing the line breaks with a `<text:line-break/>` tag.

### Control Flow

Most of the time odttpl will handle the internal composing of XML when you insert control flow tags (`{% for foo in foos %}`, `{% if bar %}`, etc and its enclosing tags. This is done by finding the present or absence of other odttpl tags within the internal XML tree.

#### Examples document structures
**Printing multiple records in a table**
![alt tag](https://github.com/renatormc/odttpl/blob/main/src/odttpl/docs/images/table_01.png)

**Conditional paragraphs**
![alt tag](https://github.com/renatormc/odttpl/blob/main/src/odttpl/docs/images/conditional_paragraph_01.png)

The last example could had been simplified into a single paragraph in Writer like:
```jinja
    {% if already_paid %}YOU ALREADY PAID{% else %}YOU HAVEN'T PAID{% endif %}
```

**Printing a list of names**
```jinja
    {% for name in names %}
        {{ name }}
    {% endfor %}
```

Automatic control flow in ODTTPL will handle the intuitive result of the above examples and similar thereof.

Although most of the time the automatic handling of control flow in odttpl may be good enough, we still provide an additional method for manual control of the flow. Use the `reference` property of the field to specify where where the control flow tag will be used or internally moved within the XML document:

* `paragraph`: Whole paragraph containing the field will be replaced with the field content.
* `before::paragraph`: Field content will be moved before the current paragraph.
* `after::paragraph`: Field content will be moved after the current paragraph.
* `row`: The entire table row containing the field will be replace with the field content.
* `before::row`: Field content will be moved before the current table row.
* `after::row`: Field content will be moved after the current table row.
* `cell`: The entire table cell will be replaced with the current field content. Even though this setting is available, it is not recommended. Generated documents may not be what you expected.
* `before::cell`: Same as `before::row` but for a table cell.
* `after::cell`: Same as `after::row` but for a table cell.
> Field content is the control flow tag you insert with the Writer *input field*

### Hyperlink  Support
LibreOffice by default escapes every URL in links, pictures or any other element supporting hyperlink functionallity. This can be a problem if you need to generate dynamic links because your template logic is URL encoded and impossible to be handled by the Jinja engine. ODTTPL solves this problem by reserving the `odttpl` URI scheme. If you need to create dynamic links in your documents, prepend every link with the `odttpl:` scheme.

So for example if you have the following dynamic link: `https://mysite/products/{{ product.id }}`, prepend it with the **`odttpl:`** scheme, leaving the final link as `odttpl:https://mysite/products/{{ product.id }}`.

### Image Support
ODTTPL allows you to use placeholder images in templates that will be replaced when rendering the final document. To create a placeholder image on your template:

1. Insert an image into the document as normal. This image will be replaced when rendering the final document.
2. Change the name of the recently added image to a Jinja2 print tag (the ones with double curly braces). The variable should call the `image` filter, i.e.: Suppose you have a client record (passed to template as `client` object), and a picture of him is stored in the `picture` field. To print the client's picture into a document set the image name to `{{ client.picture|image }}`.

> To change image name, right click under image, select "Picture..." from the popup menu and navigate to
"Options" tab.

#### Global function `image`

In addition to the `image` filter (used for placeholder replacement), ODTTPL provides a global function also named `image` that inserts an image directly at the point of call. Use it in your template like so:

```jinja
{{ image('path/to/image.jpg', w=100, h=200) }}
```

Parameters:
- `path` - Path to the image file.
- `w` - Desired width in millimeters.
- `h` - Desired height in millimeters.
- `max_w` - Maximum width in millimeters (image will be scaled down if larger).
- `max_h` - Maximum height in millimeters (image will be scaled down if larger).

If only `w` is provided, the height is calculated automatically to preserve aspect ratio, and vice versa. If both `max_w` and `max_h` are given, the image is constrained within those bounds while maintaining aspect ratio.

#### Media loader
To load image data, ODTTPL needs a media loader. The engine by default provides a file system loader which takes the variable value (specified in image name). This value can be a file object containing an image or an absolute or a relative filename to `media_path` passed at `Renderer` instance creation.

Since the default media loader is very limited. Users can provide theirs own media loader to the `Renderer` instance. A media loader can perform image retrieval and/or any required transformation of images. The media loader must take the image value from the template and return a tuple whose first item is a file object containing the image. Its second element must be the image mimetype.

Example declaring a media loader:
```python
    from . import Renderer

    engine = Renderer()

    @engine.media_loader
    def db_images_loader(value, *args, *kwargs):
        # load from images collection the image with `value` id.
        image = db.images.findOne({'_id': value})

        return (image, the_image_mimetype)

    engine.render(template, **template_vars)
```
The media loader also receive any argument or keywork arguments declared in the template. i.e: If the placeholder image's name is: `{{ client.image|image('keep_ratio', tiny=True)}}` the media loader will receive: first the value of `client.image` as it first argument; the string `keep_ratio` as an additional argument and `tiny` as a keyword argument.

The loader can also access and update the internal `draw:frame` and `draw:image` nodes. The loader receives as a dictionary the attributes of these nodes through `frame_attrs` and `image_attrs` keyword arguments. Is some update is made to these dictionary odttpl will update the internal nodes with the changes. This is useful when the placeholder's aspect radio and replacement image's aspect radio are different and you need to keep the aspect ratio of the original image.

### Builtin Filters
ODTTPL includes some predefined *jinja2* filters. Included filters are:

- **image(value)**
See *Image Support* section above.

- **markdown(value)**
Convert the value, a markdown formated string, into a ODT formated text. Example:

        {{ invoice.description|markdown }}

- **pad(value, length)**
Pad zeroes to `value` to the left until output value's length be equal to `length`. Default length if 5. Example:

        {{ invoice.number|pad(6) }}

### Features of jinja2 not supported
ODTTPL supports most of the jinja2 control structure/flow tags. But please avoid using the following tags since they are not supported: `block`, `extends`, `macro`, `call`, `include` and `import`.
