@echo off
echo ========================================
echo VIDHI - AWS Resources Setup
echo ========================================
echo.

REM Check if AWS CLI is configured
aws sts get-caller-identity >nul 2>&1
if errorlevel 1 (
    echo ERROR: AWS CLI not configured or credentials invalid
    echo Please run: aws configure
    pause
    exit /b 1
)

echo AWS CLI configured successfully!
echo.

REM Generate unique suffix using current time
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "suffix=%YYYY%%MM%%DD%%HH%%Min%"

echo Creating S3 buckets with suffix: %suffix%
echo.

REM Create S3 buckets
echo Creating S3 bucket for audio files...
aws s3 mb s3://vidhi-audio-prod-%suffix% --region ap-south-1
if errorlevel 1 (
    echo ERROR: Failed to create audio bucket
    echo Trying alternative name...
    aws s3 mb s3://vidhi-audio-%suffix% --region ap-south-1
)

echo Creating S3 bucket for documents...
aws s3 mb s3://vidhi-documents-prod-%suffix% --region ap-south-1
if errorlevel 1 (
    echo ERROR: Failed to create documents bucket
    echo Trying alternative name...
    aws s3 mb s3://vidhi-docs-%suffix% --region ap-south-1
)

echo.
echo Created S3 buckets:
aws s3 ls | findstr vidhi

echo.
echo Creating DynamoDB tables...

echo Creating users table...
aws dynamodb create-table --table-name vidhi-users --attribute-definitions AttributeName=user_id,AttributeType=S --key-schema AttributeName=user_id,KeyType=HASH --billing-mode PAY_PER_REQUEST --region ap-south-1 >nul 2>&1

echo Creating chat history table...
aws dynamodb create-table --table-name vidhi-chat-history --attribute-definitions AttributeName=chat_id,AttributeType=S AttributeName=message_id,AttributeType=S --key-schema AttributeName=chat_id,KeyType=HASH AttributeName=message_id,KeyType=RANGE --billing-mode PAY_PER_REQUEST --region ap-south-1 >nul 2>&1

echo Creating response cache table...
aws dynamodb create-table --table-name vidhi-response-cache --attribute-definitions AttributeName=query_hash,AttributeType=S --key-schema AttributeName=query_hash,KeyType=HASH --billing-mode PAY_PER_REQUEST --region ap-south-1 >nul 2>&1

echo Creating embedding cache table...
aws dynamodb create-table --table-name vidhi-embedding-cache --attribute-definitions AttributeName=text_hash,AttributeType=S --key-schema AttributeName=text_hash,KeyType=HASH --billing-mode PAY_PER_REQUEST --region ap-south-1 >nul 2>&1

echo.
echo Waiting for tables to be created (this may take 30-60 seconds)...
timeout /t 10 /nobreak >nul

echo.
echo Created DynamoDB tables:
aws dynamodb list-tables --region ap-south-1 --query "TableNames[?contains(@, 'vidhi')]" --output table

echo.
echo ========================================
echo AWS Resources Created Successfully!
echo ========================================
echo.
echo S3 Buckets:
aws s3 ls | findstr vidhi
echo.
echo DynamoDB Tables:
aws dynamodb list-tables --region ap-south-1 --query "TableNames[?contains(@, 'vidhi')]" --output text
echo.
echo Next steps:
echo 1. Copy the bucket names above
echo 2. Update your .env file with these bucket names
echo 3. Enable Bedrock models in AWS Console
echo 4. Test your backend: python app.py
echo.
echo Your .env file should contain:
echo S3_BUCKET_AUDIO=vidhi-audio-prod-%suffix%
echo S3_BUCKET_DOCUMENTS=vidhi-documents-prod-%suffix%
echo.
pause