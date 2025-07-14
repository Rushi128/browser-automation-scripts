import { OpenAI } from 'openai';
import AWS from 'aws-sdk';
import dotenv from 'dotenv';

dotenv.config();

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  organization: process.env.OPENAI_ORGANIZATION,
});

const s3 = new AWS.S3();

export const handler = async (event) => {
  try {
    // Get prompt from event
    const prompt = event.prompt;
    if (!prompt) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Missing prompt in event.' }),
      };
    }

    // Generate image
    const response = await openai.images.generate({
      model: 'gpt-image-1',
      prompt,
      n: 1,
      size: "1024x1536",
      response_format: "b64_json",
    });

    const imageBase64 = response.data[0].b64_json;
    const buffer = Buffer.from(imageBase64, 'base64');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `gpt-image-output-${timestamp}.png`;

    // Upload to S3
    const bucketName = process.env.IMAGE_BUCKET_NAME;
    if (!bucketName) {
      return {
        statusCode: 500,
        body: JSON.stringify({ error: 'IMAGE_BUCKET_NAME not set in environment.' }),
      };
    }

    await s3.putObject({
      Bucket: bucketName,
      Key: fileName,
      Body: buffer,
      ContentType: 'image/png',
    }).promise();


    // Return S3 key and URL
    return {
      statusCode: 200,
      body: JSON.stringify({
        s3_key: fileName,
      }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};