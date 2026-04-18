from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import io
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_folder='../frontend', static_url_path='')
# Enable CORS for frontend interaction
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def serve_static(path):
    if '.' not in path:
        return app.send_static_file(path + '.html')
    return app.send_static_file(path)

# Global state for the application (single-user demo)
class AppState:
    df = None
    filename = None
    cleaned = False

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Only CSV files are allowed"}), 400
        
    try:
        # Read the file
        AppState.df = pd.read_csv(file)
        AppState.filename = file.filename
        AppState.cleaned = False
        
        # Calculate stats
        rows = int(AppState.df.shape[0])
        cols = int(AppState.df.shape[1])
        missing = int(AppState.df.isna().sum().sum())
        
        return jsonify({
            "message": "File uploaded successfully",
            "filename": AppState.filename,
            "rows": rows,
            "columns": cols,
            "missing_values": missing
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clean', methods=['POST'])
def clean_data():
    if AppState.df is None:
        return jsonify({"error": "No dataset uploaded"}), 400
        
    try:
        # Remove duplicates
        initial_rows = len(AppState.df)
        AppState.df = AppState.df.drop_duplicates()
        
        # Remove nulls
        AppState.df = AppState.df.dropna()
        
        final_rows = len(AppState.df)
        AppState.cleaned = True
        
        rows_removed = initial_rows - final_rows
        
        return jsonify({
            "message": "Dataset cleaned successfully",
            "rows": int(AppState.df.shape[0]),
            "columns": int(AppState.df.shape[1]),
            "rows_removed": int(rows_removed)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze', methods=['GET'])
def analyze_data():
    if AppState.df is None:
        return jsonify({"error": "No dataset uploaded"}), 400
        
    try:
        numeric_df = AppState.df.select_dtypes(include=[np.number])
        numeric_cols = numeric_df.columns.tolist()
        
        averages = {}
        for col in numeric_cols:
            val = float(numeric_df[col].mean())
            if not np.isnan(val):
                averages[col] = val
            
        return jsonify({
            "rows": int(AppState.df.shape[0]),
            "columns": int(AppState.df.shape[1]),
            "averages": averages,
            "numeric_columns": numeric_cols,
            "status": "cleaned" if AppState.cleaned else "raw"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/report', methods=['GET'])
def generate_report():
    if AppState.df is None:
        return jsonify({"error": "No dataset uploaded"}), 400
        
    try:
        numeric_df = AppState.df.select_dtypes(include=[np.number])
        numeric_cols = numeric_df.columns.tolist()
        
        stats = {}
        averages = {}
        
        insights = []
        insights.append(f"Dataset contains {AppState.df.shape[0]} rows and {AppState.df.shape[1]} columns.")
        
        if numeric_cols:
            for col in numeric_cols:
                avg_val = float(numeric_df[col].mean())
                max_val = float(numeric_df[col].max())
                min_val = float(numeric_df[col].min())
                
                if not np.isnan(avg_val):
                    averages[col] = avg_val
                
                stats[col] = {
                    "mean": avg_val if not np.isnan(avg_val) else None,
                    "max": max_val if not np.isnan(max_val) else None,
                    "min": min_val if not np.isnan(min_val) else None
                }
                
                if not np.isnan(avg_val):
                    insights.append(f"Average for {col} is {avg_val:.2f}.")
                if not np.isnan(max_val):
                    insights.append(f"The highest value in {col} is {max_val:.2f}.")
        else:
            insights.append("No numeric columns found for deep analysis.")
            
        return jsonify({
            "dataset": AppState.filename,
            "status": "cleaned" if AppState.cleaned else "raw",
            "stats": stats,
            "averages": averages,
            "insights": insights,
            "explanation": "The AI Engine has fully processed the dataset and extracted numerical summaries. These findings highlight key aggregate metrics including mean, maximum, and minimum values which portray the distribution behavior of your numeric data fields."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_chatbot():
    if AppState.df is None:
        return jsonify({"answer": "Please upload a dataset first."})
        
    data = request.json
    if not data or 'question' not in data:
        return jsonify({"error": "No question provided"}), 400
        
    question = str(data['question']).lower()
    
    try:
        numeric_df = AppState.df.select_dtypes(include=[np.number])
        numeric_cols = [c.lower() for c in numeric_df.columns]
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return jsonify({"answer": "Error: Groq API key is missing. Please add GROQ_API_KEY to the .env file in the backend folder."})
            
        client = Groq(api_key=api_key)
        
        dataset_info = f"Dataset: {AppState.filename}\nRows: {AppState.df.shape[0]}\nColumns: {AppState.df.shape[1]}\nColumn Names: {', '.join(AppState.df.columns)}"
        
        if not numeric_df.empty:
            means = numeric_df.mean().dropna().to_dict()
            mins = numeric_df.min().dropna().to_dict()
            maxs = numeric_df.max().dropna().to_dict()
            dataset_info += f"\nNumeric Column Averages: {means}\nNumeric Column Minimums: {mins}\nNumeric Column Maximums: {maxs}"
            
        prompt = f"""You are a helpful data analyst AI for the ANALYDWO platform. 
Here is your context about the user's currently uploaded dataset:
{dataset_info}

The user asks: "{question}"
Answer the question naturally and concisely based on the dataset information provided above. If the question is entirely unrelated to data analysis or the dataset, politely redirect the conversation back to the dataset."""
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",
        )
        
        return jsonify({"answer": chat_completion.choices[0].message.content})
            
    except Exception as e:
        return jsonify({"answer": f"Error processing question: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
