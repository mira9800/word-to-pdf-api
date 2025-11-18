from flask import Flask, request, send_file
import subprocess
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return '''
    <h1>Word to PDF Converter API</h1>
    <p>Send a POST request to /convert with a Word file</p>
    <form method="post" action="/convert" enctype="multipart/form-data">
        <input type="file" name="file" accept=".doc,.docx">
        <input type="submit" value="Convert">
    </form>
    '''

@app.route('/convert', methods=['POST'])
def convert_to_pdf():
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return {'error': 'No file uploaded'}, 400
        
        file = request.files['file']
        
        if file.filename == '':
            return {'error': 'No file selected'}, 400
        
        if file and allowed_file(file.filename):
            # Generate unique filenames
            file_id = str(uuid.uuid4())
            input_filename = secure_filename(file.filename)
            input_path = f"/tmp/{file_id}_{input_filename}"
            output_path = f"/tmp/{file_id}_converted.pdf"
            
            # Save uploaded file
            file.save(input_path)
            
            # Convert to PDF using LibreOffice
            try:
                subprocess.run([
                    'libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', '/tmp', input_path
                ], check=True, timeout=30)
                
                # Find the converted PDF
                base_name = os.path.splitext(input_filename)[0]
                expected_output = f"/tmp/{base_name}.pdf"
                
                if os.path.exists(expected_output):
                    # Rename to our expected output path
                    os.rename(expected_output, output_path)
                    
                    # Send the PDF file
                    return send_file(
                        output_path,
                        as_attachment=True,
                        download_name=f"{base_name}.pdf",
                        mimetype='application/pdf'
                    )
                else:
                    return {'error': 'Conversion failed - output not found'}, 500
                    
            except subprocess.TimeoutExpired:
                return {'error': 'Conversion timeout'}, 500
            except subprocess.CalledProcessError:
                return {'error': 'Conversion process failed'}, 500
            finally:
                # Clean up temporary files
                for temp_file in [input_path, output_path]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
        else:
            return {'error': 'Invalid file type. Please upload .doc or .docx'}, 400
            
    except Exception as e:
        return {'error': f'Server error: {str(e)}'}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
