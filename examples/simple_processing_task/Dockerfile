FROM python:3.8.10
COPY . /app
RUN pip install fastapi
RUN pip install uvicorn
RUN pip install py-ce-forms-api
WORKDIR /app
CMD ["uvicorn", "--factory", "main:create_app", "--host", "0.0.0.0", "--port", "8000"]




