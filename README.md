# PDF Compressor

A simple and efficient web application to compress PDF files online using Python and Flask. Reduce file size while maintaining quality.

## Features

- 📤 **Easy Upload**: Drag and drop or click to upload PDF or JPG files
- 🧩 **Modern Interface**: Responsive grid layout with a header logo, drag-and-drop areas, dark mode toggle, progress indicators, previews, and quick navigation links
- 🎚️ **Quality Options**: Choose between high, medium, or low quality compression (PDFs) or image compression (JPG)
- 📊 **File Statistics**: View original size, compressed size, and reduction percentage
- 💾 **Quick Download**: Download compressed files instantly
- 🔒 **Secure Processing**: Files are automatically deleted after 24 hours
- 📱 **Responsive Design**: Works on desktop and mobile devices
- ❌ **Clean Interface**: Simple and intuitive user interface

### Additional Features

- 🖼️ **JPG Compressor**: Reduce the size of JPEG images with adjustable quality settings
- 📺 **JPG to 4K**: Upscale a JPEG image to 3840x2160 resolution (4K)
- 📐 **Merge PDFs**: Combine two or more PDF files into one
- ✂️ **Split PDF**: Extract specific pages from a PDF
- 📝 **PDF to Word**: Convert PDF documents to editable Word format
- 📊 **PDF to Excel**: Extract tables from a PDF and save as an Excel workbook (requires tabula-py)
- ✏️ **Edit PDF**: Rotate or delete pages from a PDF file

## Requirements

- Python 3.7+
- pip (Python package manager)
- **Tesseract OCR** (for OCR feature)
- **Java runtime** (for PDF to Excel via tabula-py)

Install Tesseract from https://github.com/tesseract-ocr/tesseract and ensure `tesseract` is on your PATH.

## Installation

1. Navigate to the project directory:
   ```bash
   cd "Python foundation course"
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to a friendly URL such as:
   ```
   http://pdf-tools.local:5000
   ```

   (You can also use `http://localhost:5000` or set up a custom host entry for `pdf-tools.local`.)

3. Upload a PDF file by dragging and dropping or clicking the upload area

4. Select your desired compression level:
   - **High Quality**: Less compression, larger file size
   - **Medium Quality**: Balanced compression
   - **Low Quality**: Maximum compression, smaller file size

5. Click "Compress PDF" and wait for the compression to complete

6. Download your compressed PDF file

## SEO & Hosting Tips

To help your site rank higher when people search for "pdf tools":

1. **Host the application on a public, meaningful domain** (e.g. `https://pdf-tools.example.com` or `https://pdf-tools.local` with local DNS entries).
2. **Include descriptive metadata** in your pages (see `<meta name="description">` and `<meta name="keywords">` in `public/index.html`).
3. **Submit your site to search engines** using tools like Google Search Console or Bing Webmaster.
4. **Build external links** from blogs, forums, social media, or other websites pointing to your site.
5. **Ensure HTTPS is enabled** and the site is mobile‑friendly (already supported in the frontend).

Search result position is ultimately controlled by search engines; these steps improve your chances but can't guarantee a #1 ranking.

## Project Structure

```
pdf-compressor/
├── public/
│   ├── index.html          # Main HTML file
│   ├── styles.css          # CSS styling
│   └── script.js           # Frontend JavaScript
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore file
└── README.md              # This file
```

## Technical Details

- **Backend**: Python with Flask framework
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **PDF Processing**: PyPDF2 library
- **Server**: Flask built-in development server

## Temporary Folders

The application creates two temporary folders:
- `uploads/` - Stores uploaded PDF files temporarily
- `downloads/` - Stores compressed PDF files for download

Both folders are automatically cleaned up (files older than 24 hours are deleted).

## API Endpoints

### GET /
Returns the main HTML page

### POST /compress
Compresses a PDF file

### POST /compress-jpg
Compresses a JPEG image

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `image`: JPG file (required)
  - `quality`: Compression level - 'high', 'medium', or 'low' (optional, default: 'medium')

**Response:**
```json
{
  "success": true,
  "message": "Image compressed successfully",
  "fileName": "filename-compressed.jpg",
  "originalSize": 123456,
  "compressedSize": 78910,
  "reduction": "35.21",
  "downloadUrl": "/download/filename-compressed.jpg"
}
```

### POST /jpg-to-4k
Upscales a JPEG image to 4K resolution (3840×2160).

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `image`: JPG file (required)

**Response:**
```json
{
  "success": true,
  "message": "Image converted to 4K successfully",
  "fileName": "filename-4k.jpg",
  "originalSize": 123456,
  "newSize": 345678,
  "downloadUrl": "/download/filename-4k.jpg"
}
```

### POST /merge
Combine two or more PDF documents into a single file.

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `pdfs`: multiple PDF files (minimum 2)

**Response:**
```json
{
  "success": true,
  "message": "Successfully merged 3 PDFs",
  "fileName": "merged-1616161616.pdf",
  "fileSize": 1024000,
  "downloadUrl": "/download/merged-1616161616.pdf"
}
```

### POST /split
Extract specific pages from a PDF and download as a new file.

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `pdf`: PDF file (required)
  - `pages`: page specifier (e.g. `1,3,5-7`)

**Response:**
```json
{
  "success": true,
  "message": "Successfully extracted 4 page(s)",
  "fileName": "original-split.pdf",
  "downloadUrl": "/download/original-split.pdf"
}
```

### POST /pdf-to-word
Convert a PDF file to a Word document (.docx).

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `pdf`: PDF file (required)

**Response:**
```json
{
  "success": true,
  "message": "PDF converted to Word successfully",
  "fileName": "filename-converted.docx",
  "fileSize": 204800,
  "downloadUrl": "/download/filename-converted.docx"
}
```

### POST /pdf-to-excel
Extract tables from a PDF into an Excel workbook. Requires `tabula-py` (Java runtime needed).

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `pdf`: PDF file (required)

**Response:**
```json
{
  "success": true,
  "message": "PDF converted to Excel successfully",
  "fileName": "filename-converted.xlsx",
  "fileSize": 307200,
  "downloadUrl": "/download/filename-converted.xlsx"
}
```

### POST /edit-pdf
Perform basic edits on a PDF such as rotating or deleting pages.

### POST /ocr
Extract text from an uploaded PDF or image using OCR.

### POST /watermark
Add a text watermark to every page of a PDF.

### POST /protect
Encrypt a PDF with a password.

### POST /reorder
Reorder pages in a PDF. Specify order as comma-separated page numbers.

### POST /convert-image
Convert an image to another format (jpg, png, webp, bmp).

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `pdf`: PDF file (required)
  - `operation`: either `rotate` or `delete`
  - `pages`: page specifier (e.g. `1-3,5`)
  - `angle`: degrees to rotate (required for `rotate`, e.g. `90`)

**Response:**
```json
{
  "success": true,
  "message": "PDF edited successfully",
  "fileName": "filename-edited.pdf",
  "downloadUrl": "/download/filename-edited.pdf"
}
```

**Request:**
- Content-Type: multipart/form-data
- Body:
  - `pdf`: PDF file (required)
  - `quality`: Compression level - 'high', 'medium', or 'low' (optional, default: 'medium')

**Response:**
```json
{
  "success": true,
  "message": "PDF compressed successfully",
  "fileName": "filename-compressed.pdf",
  "originalSize": 1024000,
  "compressedSize": 512000,
  "reduction": "50.00",
  "downloadUrl": "/download/filename-compressed.pdf"
}
```

### GET /download/<filename>
Downloads a compressed PDF file

## Limitations

- Maximum file size: 100 MB
- Only PDF files are supported
- Files are automatically deleted after 24 hours

## Configuration

To change the port, edit `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Change 5000 to your desired port
```

## Troubleshooting

### Dependencies Not Installing
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Port Already in Use
If port 5000 is already in use, change it in `app.py` to another port (e.g., 8000, 3000)

### Large Files Take Too Long
For very large files:
1. Try using "Low Quality" compression for maximum compression
2. Break up the file into smaller parts if possible

### Module Not Found Error
Make sure you're in the project directory and have installed all dependencies:
```bash
pip install -r requirements.txt
```

## Performance Tips

- Use "High Quality" for documents where clarity is important
- Use "Low Quality" for archival or less critical documents
- For best results, ensure your PDF file is not already heavily compressed

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Security

- Files are processed server-side
- Uploaded files are temporarily stored and automatically deleted
- No file information is logged or stored permanently
- All file uploads are handled with proper validation
- Filenames are sanitized before saving

## License

MIT License

## Support

For issues or feature requests:
1. Check the console for error messages
2. Ensure Python and required packages are installed correctly
3. Verify the port is not in use by another application
4. Check that the uploads and downloads folders exist and are writable

---

**Note**: This is a local application. For production use, consider:
- Adding user authentication
- Implementing file encryption
- Using a production WSGI server (Gunicorn, uWSGI)
- Adding API rate limiting
- Setting up HTTPS/SSL
- Using a cloud storage solution for files
- Adding PDF optimization features
