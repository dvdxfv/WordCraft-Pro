FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# PyMuPDF / pdfplumber 等需要编译工具链
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc g++ libffi-dev libxml2-dev libxslt1-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# 生产用 waitress，不用 flask 开发服务器
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "web.flask_app:app"]
