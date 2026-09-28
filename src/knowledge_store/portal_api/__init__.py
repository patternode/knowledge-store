"""The portal API: a Lambda behind API Gateway (HTTP API, Cognito JWT authorizer) that serves
the projection (pipeline/project.py) and answers questions over it.

It imports nothing beyond the standard library and boto3, which the Lambda runtime provides,
so Terraform packages it as a zip straight from source (no image build before the first apply).
"""
