FROM python:3.10.12
COPY . /app
RUN pip install fastapi
RUN pip install uvicorn
RUN pip install py-ce-forms-api==0.1.5
WORKDIR /app
CMD ["uvicorn", "--factory", "main:create_app", "--host", "0.0.0.0", "--port", "8000"]




