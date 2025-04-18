#!/bin/bash

source .env

gcloud run deploy \
	my-fastapi-service \
	--source . \
	--platform managed \
	--region us-central1 \
	--set-env-vars AI_API_KEY=$AI_API_KEY,LANGFUSE_SECRET_KEY=$LANGFUSE_SECRET_KEY,LANGFUSE_PUBLIC_KEY=$LANGFUSE_PUBLIC_KEY,LANGFUSE_HOST=$LANGFUSE_HOST \
	--allow-unauthenticated