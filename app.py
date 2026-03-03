from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os
from PyPDF2 import PdfReader, PdfWriter
import io
from datetime import datetime
import threading
import time
from PIL import Image
from pdf2docx import Converter
import pandas as pd
try:
    import tabula
except ImportError:
    tabula = None  # pdf-to-excel feature requires tabula-py

app = Flask(__name__, template_folder='public', static_folder='public', static_url_path='')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp'}

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, file_type='pdf'):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if file_type == 'image':
        return ext in {'jpg', 'jpeg', 'png', 'gif', 'bmp'}
    elif file_type == 'pdf':
        return ext == 'pdf'
    return ext in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Remove files older than 24 hours"""
    def cleanup():
        while True:
            time.sleep(3600)  # Check every hour
            now = time.time()
            for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER]:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        filepath = os.path.join(folder, filename)
                        if os.path.isfile(filepath):
                            if os.stat(filepath).st_mtime < now - 24 * 3600:
                                try:
                                    os.remove(filepath)
                                except:
                                    pass
    
    thread = threading.Thread(target=cleanup, daemon=True)
    thread.start()

def compress_pdf(input_path, quality='medium'):
    """
    Compress PDF file using PyPDF2
    
    Args:
        input_path: Path to input PDF file
        quality: Compression quality ('high', 'medium', 'low')
    
    Returns:
        Compressed PDF bytes and compression info
    """
    try:
        # Read the PDF
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # Set compression level based on quality
        if quality == 'high':
            compress_content_streams = False
        elif quality == 'medium':
            compress_content_streams = True
        else:  # low
            compress_content_streams = True
        
        # Copy pages with compression
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            
            if compress_content_streams and quality == 'low':
                # For low quality, compress images more aggressively
                page.compress_content_streams()
            
            writer.add_page(page)
        
        # If low quality, compress the entire document
        if quality == 'low':
            for page_num in range(len(writer.pages)):
                writer.pages[page_num].compress_content_streams()
        
        # Write to bytes
        output_bytes = io.BytesIO()
        writer.write(output_bytes)
        output_bytes.seek(0)
        
        return output_bytes.getvalue()
    
    except Exception as e:
        raise Exception(f"PDF compression failed: {str(e)}")

def merge_pdfs(file_paths):
    """Merge multiple PDF files into one"""
    try:
        writer = PdfWriter()
        
        for file_path in file_paths:
            reader = PdfReader(file_path)
            for page in reader.pages:
                writer.add_page(page)
        
        output_bytes = io.BytesIO()
        writer.write(output_bytes)
        output_bytes.seek(0)
        
        return output_bytes.getvalue()
    except Exception as e:
        raise Exception(f"PDF merge failed: {str(e)}")

def split_pdf(input_path, pages_to_extract):
    """Split PDF by extracting specific pages"""
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for page_num in pages_to_extract:
            if 0 <= page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])
        
        output_bytes = io.BytesIO()
        writer.write(output_bytes)
        output_bytes.seek(0)
        
        return output_bytes.getvalue()
    except Exception as e:
        raise Exception(f"PDF split failed: {str(e)}")

def get_pdf_info(input_path):
    """Get PDF information"""
    try:
        reader = PdfReader(input_path)
        num_pages = len(reader.pages)
        
        metadata = reader.metadata
        title = metadata.title if metadata and metadata.title else "N/A"
        author = metadata.author if metadata and metadata.author else "N/A"
        
        return {
            'num_pages': num_pages,
            'title': title,
            'author': author
        }
    except Exception as e:
        raise Exception(f"Failed to read PDF info: {str(e)}")

def images_to_pdf(image_paths):
    """Convert multiple images to a single PDF"""
    try:
        images = []
        for img_path in image_paths:
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        
        output_bytes = io.BytesIO()
        images[0].save(output_bytes, format='PDF', save_all=True, append_images=images[1:])
        output_bytes.seek(0)
        
        return output_bytes.getvalue()
    except Exception as e:
        raise Exception(f"Image to PDF conversion failed: {str(e)}")


def compress_image(input_path, quality='medium'):
    """Compress a JPEG image using Pillow.

    Args:
        input_path: path to the source image file (must be JPG/JPEG).
        quality: one of 'high', 'medium', 'low' which maps to JPEG quality levels.

    Returns:
        Compressed image bytes.
    """
    try:
        # Map abstract quality names to numeric values
        quality_map = {
            'high': 85,
            'medium': 60,
            'low': 30
        }
        q = quality_map.get(quality, 60)

        img = Image.open(input_path)
        # convert to RGB if necessary (e.g. PNG with alpha)
        if img.mode in ('RGBA', 'P'):  # palette/image with transparency
            img = img.convert('RGB')
        # always save as JPEG
        output_bytes = io.BytesIO()
        img.save(output_bytes, format='JPEG', quality=q, optimize=True)
        output_bytes.seek(0)
        return output_bytes.getvalue()
    except Exception as e:
        raise Exception(f"Image compression failed: {str(e)}")


def upscale_to_4k(input_path):
    """Resize an image to 4K resolution (3840x2160) using Pillow.

    The image is converted to RGB and resized with LANCZOS filter. If the
    original aspect ratio differs, the image will be stretched to fit exactly
    3840x2160.

    Returns the 4K image bytes (JPEG format).
    """
    try:
        img = Image.open(input_path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        # resize to 4k
        img4k = img.resize((3840, 2160), Image.LANCZOS)
        output_bytes = io.BytesIO()
        img4k.save(output_bytes, format='JPEG', quality=90, optimize=True)
        output_bytes.seek(0)
        return output_bytes.getvalue()
    except Exception as e:
        raise Exception(f"Upscaling to 4K failed: {str(e)}")

def pdf_to_word(input_path, output_path):
    """Convert PDF to Word document"""
    try:
        cv = Converter(input_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()
        return True
    except Exception as e:
        raise Exception(f"PDF to Word conversion failed: {str(e)}")


def ocr_file(input_path, is_image=False):
    """Extract text via OCR from PDF or image file"""
    try:
        from pytesseract import image_to_string
        if is_image:
            img = Image.open(input_path)
            text = image_to_string(img)
            return text
        else:
            # convert each page to image then OCR
            reader = PdfReader(input_path)
            text_out = []
            for page in reader.pages:
                # render page to image using pdf2image if available
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(input_path, first_page=reader.pages.index(page)+1, last_page=reader.pages.index(page)+1)
                    for img in images:
                        text_out.append(image_to_string(img))
                except Exception:
                    # fallback: metadata only
                    continue
            return "\n".join(text_out)
    except Exception as e:
        raise Exception(f"OCR failed: {str(e)}")


def watermark_pdf(input_path, text):
    """Add a simple text watermark to every page of a PDF"""
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import tempfile

        reader = PdfReader(input_path)
        writer = PdfWriter()

        # create watermark PDF
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFont("Helvetica", 40)
        can.setFillColorRGB(0.6,0.6,0.6, alpha=0.3)
        can.drawCentredString(300, 500, text)
        can.save()
        packet.seek(0)
        watermark = PdfReader(packet)

        for page in reader.pages:
            page.merge_page(watermark.pages[0])
            writer.add_page(page)

        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        return out.getvalue()
    except Exception as e:
        raise Exception(f"Watermark failed: {str(e)}")


def protect_pdf(input_path, password):
    """Encrypt PDF with a password"""
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        return out.getvalue()
    except Exception as e:
        raise Exception(f"PDF protection failed: {str(e)}")


def reorder_pdf(input_path, order_list):
    """Reorder pages according to zero-based indices list"""
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        num = len(reader.pages)
        for idx in order_list:
            if 0 <= idx < num:
                writer.add_page(reader.pages[idx])
        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        return out.getvalue()
    except Exception as e:
        raise Exception(f"Reorder failed: {str(e)}")


def convert_image_format(input_path, target_format):
    """Convert an image to target format (jpg, png, webp, bmp)
    Returns bytes of converted image.
    """
    try:
        img = Image.open(input_path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        out = io.BytesIO()
        img.save(out, format=target_format.upper())
        out.seek(0)
        return out.getvalue()
    except Exception as e:
        raise Exception(f"Image conversion failed: {str(e)}")


def pdf_to_excel(input_path, output_path):
    """Convert tables in a PDF to an Excel workbook using tabula-py."""
    if tabula is None:
        raise Exception("tabula-py is not installed. Install it via requirements.txt.")
    try:
        # read all tables from the PDF
        dfs = tabula.read_pdf(input_path, pages='all', multiple_tables=True)
        if not dfs:
            raise Exception("No tables found in PDF")
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for idx, df in enumerate(dfs):
                sheet = f"Table{idx+1}"
                df.to_excel(writer, sheet_name=sheet, index=False)
        return True
    except Exception as e:
        raise Exception(f"PDF to Excel conversion failed: {str(e)}")


def edit_pdf(input_path, operations):
    """Apply simple edit operations to a PDF.
    operations: dict containing keys 'operation', 'pages' (list of zero-based indices),
    and optionally 'angle' for rotate.
    Supported operations: 'rotate', 'delete'.
    """
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        pages_to_modify = operations.get('pages', [])
        op = operations.get('operation')
        angle = operations.get('angle', 0)

        for i, page in enumerate(reader.pages):
            # skip pages when deleting
            if op == 'delete' and i in pages_to_modify:
                continue

            new_page = page
            if op == 'rotate' and i in pages_to_modify:
                # rotation must be clockwise
                new_page = page.rotate_clockwise(angle)

            writer.add_page(new_page)

        out_bytes = io.BytesIO()
        writer.write(out_bytes)
        out_bytes.seek(0)
        return out_bytes.getvalue()
    except Exception as e:
        raise Exception(f"PDF edit failed: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compress', methods=['POST'])
def compress():
    try:
        # Check if file is provided
        if 'pdf' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['pdf']
        quality = request.form.get('quality', 'medium')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        # Get original file size
        original_size = os.path.getsize(input_path)
        
        # Compress PDF
        compressed_bytes = compress_pdf(input_path, quality)
        compressed_size = len(compressed_bytes)
        
        # Calculate reduction percentage
        reduction = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0
        
        # Save compressed file
        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}-compressed.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(compressed_bytes)
        
        # Clean up uploaded file
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'PDF compressed successfully',
            'fileName': output_filename,
            'originalSize': original_size,
            'compressedSize': compressed_size,
            'reduction': f"{reduction:.2f}",
            'downloadUrl': f'/download/{output_filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    try:
        file_path = os.path.join(DOWNLOAD_FOLDER, secure_filename(filename))
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch-compress', methods=['POST'])
def batch_compress():
    try:
        if 'pdfs' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('pdfs')
        quality = request.form.get('quality', 'medium')
        
        if not files or len(files) == 0:
            return jsonify({'error': 'Please select at least one PDF'}), 400
        
        results = []
        file_paths = []
        
        for file in files:
            if file.filename == '' or not allowed_file(file.filename):
                continue
            
            filename = secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)
            file_paths.append(input_path)
            
            try:
                original_size = os.path.getsize(input_path)
                compressed_bytes = compress_pdf(input_path, quality)
                compressed_size = len(compressed_bytes)
                reduction = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0
                
                base_name = filename.rsplit('.', 1)[0]
                output_filename = f"{base_name}-compressed.pdf"
                output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
                
                with open(output_path, 'wb') as f:
                    f.write(compressed_bytes)
                
                results.append({
                    'fileName': output_filename,
                    'originalSize': original_size,
                    'compressedSize': compressed_size,
                    'reduction': f"{reduction:.2f}",
                    'downloadUrl': f'/download/{output_filename}'
                })
            except Exception as e:
                results.append({
                    'fileName': filename,
                    'error': str(e)
                })
        
        # Cleanup uploaded files
        for path in file_paths:
            try:
                os.remove(path)
            except:
                pass
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(results)} file(s)',
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/merge', methods=['POST'])
def merge():
    try:
        if 'pdfs' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('pdfs')
        
        if not files or len(files) < 2:
            return jsonify({'error': 'Please select at least 2 PDFs to merge'}), 400
        
        file_paths = []
        
        for file in files:
            if file.filename == '' or not allowed_file(file.filename):
                continue
            
            filename = secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)
            file_paths.append(input_path)
        
        # Merge PDFs
        merged_bytes = merge_pdfs(file_paths)
        merged_size = len(merged_bytes)
        
        # Save merged file
        output_filename = f"merged-{int(time.time())}.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(merged_bytes)
        
        # Cleanup uploaded files
        for path in file_paths:
            try:
                os.remove(path)
            except:
                pass
        
        return jsonify({
            'success': True,
            'message': f'Successfully merged {len(file_paths)} PDFs',
            'fileName': output_filename,
            'fileSize': merged_size,
            'downloadUrl': f'/download/{output_filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/split', methods=['POST'])
def split():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['pdf']
        pages_range = request.form.get('pages', '')
        
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid PDF file'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        # Parse pages range (e.g., "1,3,5-7" means pages 1, 3, 5, 6, 7)
        pages_to_extract = []
        if pages_range:
            for part in pages_range.split(','):
                if '-' in part:
                    start, end = part.split('-')
                    pages_to_extract.extend(range(int(start.strip())-1, int(end.strip())))
                else:
                    pages_to_extract.append(int(part.strip())-1)
        
        # Split PDF
        split_bytes = split_pdf(input_path, pages_to_extract)
        
        # Save split file
        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}-split.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(split_bytes)
        
        # Cleanup
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': f'Successfully extracted {len(set(pages_to_extract))} page(s)',
            'fileName': output_filename,
            'downloadUrl': f'/download/{output_filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/info', methods=['POST'])
def info():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['pdf']
        
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid PDF file'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        file_size = os.path.getsize(input_path)
        pdf_info = get_pdf_info(input_path)
        
        # Cleanup
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'fileName': filename,
            'fileSize': file_size,
            'numPages': pdf_info['num_pages'],
            'title': pdf_info['title'],
            'author': pdf_info['author']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/jpg-to-pdf', methods=['POST'])
def jpg_to_pdf():
    try:
        if 'images' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('images')
        
        if not files or len(files) == 0:
            return jsonify({'error': 'Please select at least one image'}), 400
        
        image_paths = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if not allowed_file(file.filename, 'image'):
                return jsonify({'error': f'Invalid file type: {file.filename}. Only JPG, PNG, GIF, BMP allowed'}), 400
            
            filename = secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)
            image_paths.append(input_path)
        
        # Convert images to PDF
        pdf_bytes = images_to_pdf(image_paths)
        
        # Save PDF
        output_filename = f"images-to-pdf-{int(time.time())}.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Cleanup uploaded files
        for path in image_paths:
            try:
                os.remove(path)
            except:
                pass
        
        return jsonify({
            'success': True,
            'message': f'Successfully converted {len(image_paths)} image(s) to PDF',
            'fileName': output_filename,
            'fileSize': len(pdf_bytes),
            'downloadUrl': f'/download/{output_filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# new endpoint for JPEG compression
@app.route('/compress-jpg', methods=['POST'])
def compress_jpg():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['image']
        quality = request.form.get('quality', 'medium')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Only allow image types
        if not allowed_file(file.filename, 'image'):
            return jsonify({'error': 'Only image files are allowed'}), 400
        # restrict to jpg/jpeg
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in ('jpg', 'jpeg'):
            return jsonify({'error': 'JPEG compressor only supports JPG/JPEG files'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        original_size = os.path.getsize(input_path)
        compressed_bytes = compress_image(input_path, quality)
        compressed_size = len(compressed_bytes)
        reduction = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0
        
        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}-compressed.jpg"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(compressed_bytes)
        
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Image compressed successfully',
            'fileName': output_filename,
            'originalSize': original_size,
            'compressedSize': compressed_size,
            'reduction': f"{reduction:.2f}",
            'downloadUrl': f'/download/{output_filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# new endpoint for 4K upscaling
@app.route('/jpg-to-4k', methods=['POST'])
def jpg_to_4k():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'image'):
            return jsonify({'error': 'Only image files are allowed'}), 400
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in ('jpg', 'jpeg'):
            return jsonify({'error': '4K converter only supports JPG/JPEG files'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        original_size = os.path.getsize(input_path)
        upscaled_bytes = upscale_to_4k(input_path)
        upscaled_size = len(upscaled_bytes)
        
        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}-4k.jpg"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(upscaled_bytes)
        
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Image converted to 4K successfully',
            'fileName': output_filename,
            'originalSize': original_size,
            'newSize': upscaled_size,
            'downloadUrl': f'/download/{output_filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word_route():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['pdf']
        
        if file.filename == '' or not allowed_file(file.filename, 'pdf'):
            return jsonify({'error': 'Invalid PDF file'}), 400
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        # Create output filename
        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}-converted.docx"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        
        # Convert PDF to Word
        pdf_to_word(input_path, output_path)
        
        output_size = os.path.getsize(output_path)
        
        # Cleanup uploaded file
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'PDF converted to Word successfully',
            'fileName': output_filename,
            'fileSize': output_size,
            'downloadUrl': f'/download/{output_filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# new endpoint for PDF to Excel conversion
@app.route('/pdf-to-excel', methods=['POST'])
def pdf_to_excel_route():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['pdf']
        if file.filename == '' or not allowed_file(file.filename, 'pdf'):
            return jsonify({'error': 'Invalid PDF file'}), 400

        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}-converted.xlsx"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)

        # Convert PDF tables to Excel
        pdf_to_excel(input_path, output_path)

        output_size = os.path.getsize(output_path)
        try:
            os.remove(input_path)
        except:
            pass

        return jsonify({
            'success': True,
            'message': 'PDF converted to Excel successfully',
            'fileName': output_filename,
            'fileSize': output_size,
            'downloadUrl': f'/download/{output_filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# new endpoint for editing a PDF (rotate/delete pages)
@app.route('/edit-pdf', methods=['POST'])
def edit_pdf_route():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['pdf']
        if file.filename == '' or not allowed_file(file.filename, 'pdf'):
            return jsonify({'error': 'Invalid PDF file'}), 400

        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        operation = request.form.get('operation', '')
        pages_str = request.form.get('pages', '')
        angle = int(request.form.get('angle', '0')) if request.form.get('angle') else 0

        pages = []
        if pages_str:
            for part in pages_str.split(','):
                if '-' in part:
                    start, end = part.split('-')
                    pages.extend(range(int(start.strip())-1, int(end.strip())))
                else:
                    pages.append(int(part.strip())-1)

        operations = {
            'operation': operation,
            'pages': pages,
            'angle': angle
        }

        edited_bytes = edit_pdf(input_path, operations)

        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}-edited.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)

        with open(output_path, 'wb') as f:
            f.write(edited_bytes)

        try:
            os.remove(input_path)
        except:
            pass

            return jsonify({
            'success': True,
            'message': 'PDF edited successfully',
            'fileName': output_filename,
            'downloadUrl': f'/download/{output_filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# OCR endpoint (PDF or image)
@app.route('/ocr', methods=['POST'])
def ocr_route():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        ext = filename.rsplit('.',1)[1].lower()
        is_image = ext in {'jpg','jpeg','png','gif','bmp'}
        text = ocr_file(input_path, is_image=is_image)
        try:
            os.remove(input_path)
        except:
            pass
        return jsonify({'success': True, 'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# watermark
@app.route('/watermark', methods=['POST'])
def watermark_route():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['pdf']
        text = request.form.get('text', '')
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid PDF file'}), 400
        if not text:
            return jsonify({'error': 'No watermark text provided'}), 400
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        watermarked = watermark_pdf(input_path, text)
        base = filename.rsplit('.',1)[0]
        output_filename = f"{base}-watermarked.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        with open(output_path,'wb') as f:
            f.write(watermarked)
        try:
            os.remove(input_path)
        except:
            pass
        return jsonify({'success': True,'fileName': output_filename,'downloadUrl':f'/download/{output_filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# protect
@app.route('/protect', methods=['POST'])
def protect_route():
    try:
        if 'pdf' not in request.files or 'password' not in request.form:
            return jsonify({'error': 'Missing parameters'}), 400
        file = request.files['pdf']
        pwd = request.form.get('password')
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid PDF file'}), 400
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        protected = protect_pdf(input_path, pwd)
        base = filename.rsplit('.',1)[0]
        output_filename = f"{base}-protected.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        with open(output_path,'wb') as f:
            f.write(protected)
        try:
            os.remove(input_path)
        except:
            pass
        return jsonify({'success': True,'fileName': output_filename,'downloadUrl':f'/download/{output_filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# reorder
@app.route('/reorder', methods=['POST'])
def reorder_route():
    try:
        if 'pdf' not in request.files or 'order' not in request.form:
            return jsonify({'error': 'Missing parameters'}), 400
        file = request.files['pdf']
        order_str = request.form.get('order')
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid PDF file'}), 400
        order_list = []
        for part in order_str.split(','):
            try:
                order_list.append(int(part.strip())-1)
            except:
                pass
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        reordered = reorder_pdf(input_path, order_list)
        base = filename.rsplit('.',1)[0]
        output_filename = f"{base}-reordered.pdf"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        with open(output_path,'wb') as f:
            f.write(reordered)
        try:
            os.remove(input_path)
        except:
            pass
        return jsonify({'success': True,'fileName': output_filename,'downloadUrl':f'/download/{output_filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# image format conversion
@app.route('/convert-image', methods=['POST'])
def convert_image_route():
    try:
        if 'image' not in request.files or 'format' not in request.form:
            return jsonify({'error': 'Missing parameters'}), 400
        file = request.files['image']
        fmt = request.form.get('format','jpg').lower()
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not allowed_file(file.filename, 'image'):
            return jsonify({'error': 'Invalid image file'}), 400
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        converted_bytes = convert_image_format(input_path, fmt)
        base = filename.rsplit('.',1)[0]
        output_filename = f"{base}-converted.{fmt}"
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        with open(output_path,'wb') as f:
            f.write(converted_bytes)
        try:
            os.remove(input_path)
        except:
            pass
        return jsonify({'success': True,'fileName': output_filename,'downloadUrl':f'/download/{output_filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
        # Cleanup uploaded file
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'PDF converted to Word successfully',
            'fileName': output_filename,
            'fileSize': output_size,
            'downloadUrl': f'/download/{output_filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start cleanup thread
    cleanup_old_files()
    
    print("\n" + "="*50)
    print("📄 PDF Compressor is running!")
    print("="*50)
    print("Open your browser and go to: http://pdf-tools.local:5000")
    print("="*50 + "\n")
    
    app.run(debug=True, port=8000)
