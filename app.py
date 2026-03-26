"""
NL-to-SQL Pipeline - Flask Web Application

A modular pipeline for converting natural language to SQL using
LLMs via Z.AI API (OpenAI SDK compatible).

Security features:
- Prompt injection detection and prevention
- Input validation and sanitization
- Output monitoring for data leakage
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import traceback
import os

from pipeline.core import NL2SQLPipeline
from config import ENABLE_SECURITY_LOGGING

app = Flask(__name__)

# Initialize the pipeline (same instance used everywhere)
pipeline = NL2SQLPipeline(enable_security_logging=ENABLE_SECURITY_LOGGING)


@app.route('/')
def index():
    """Serve the main UI."""
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    """
    Generate SQL from natural language question.
    
    Expects JSON body with:
    - schema: Database schema (CREATE TABLE statements)
    - question: Natural language question
    
    Returns JSON with:
    - success: Boolean
    - sql: Generated SQL query
    - reasoning: Chain-of-thought explanation
    - verification: Verification status and any corrections
    - disclaimer: Security notice about SQL execution
    - error: Error message if failed
    """
    try:
        data = request.get_json()
        
        schema = data.get('schema', '')
        question = data.get('question', '')
        
        # Run the pipeline
        result = pipeline.generate(question, schema, include_answer=True)
        
        if not result.success:
            # Different response for security blocks vs other errors
            if result.security_blocked:
                return jsonify({
                    'success': False,
                    'error': result.error,
                    'security_blocked': True
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': result.error
                }), 400
        
        return jsonify({
            'success': True,
            'sql': result.sql,
            'reasoning': result.reasoning,
            'answer': result.answer,
            'verification': {
                'is_valid': result.is_valid,
                'corrections_made': result.corrections_made,
                'notes': result.verification_notes
            },
            'disclaimer': result.disclaimer
        })
        
    except Exception as e:
        # Unexpected errors
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


# Serve static files from public/ directory (for Vercel compatibility)
# This allows /styles.css to work locally, matching Vercel's behavior
# Must be defined LAST so specific routes are matched first
@app.route('/<path:filename>')
def serve_public(filename):
    """Serve static files from public/ directory."""
    # Only serve files with static file extensions
    static_extensions = ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')
    if not filename.lower().endswith(static_extensions):
        from flask import abort
        abort(404)
    
    public_dir = os.path.join(os.path.dirname(__file__), 'public')
    file_path = os.path.join(public_dir, filename)
    if os.path.exists(file_path):
        return send_from_directory(public_dir, filename)
    # If file doesn't exist in public/, let Flask handle 404
    from flask import abort
    abort(404)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("NL-to-SQL Pipeline (Secured)")
    print("=" * 60)
    print("\nSecurity features enabled:")
    print("  - Prompt injection detection")
    print("  - Input validation and sanitization")
    print("  - Output monitoring for data leakage")
    print(f"  - Security logging: {'enabled' if ENABLE_SECURITY_LOGGING else 'disabled'}")
    print("\nStarting server at http://localhost:5000")
    print("\n" + "=" * 60 + "\n")
    
    app.run(debug=True, port=5000)