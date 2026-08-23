#!/bin/bash

cd Database\ Infra/
docker compose up -d
cd ../Backend
uvicorn app.main:app --reload