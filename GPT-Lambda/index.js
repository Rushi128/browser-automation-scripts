import { OpenAI } from 'openai';
import AWS from 'aws-sdk';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  organization: process.env.OPENAI_ORGANIZATION,
});

const s3 = new AWS.S3();

export const handler = async (event) => {
  try {
    // Get prompt from event
    const prompt = event.prompt;
    const imgcount = event.imgcount;

    if (!prompt) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Missing prompt in event.' }),
      };
    }

    console.log('Received prompt:', prompt);

    // Generate image
    const response = await openai.images.generate({
      model: 'gpt-image-1',
      prompt,
      n: imgcount,
      size: "1024x1536"
    });

    const imageBase64 = response.data[0].b64_json;
    const buffer = Buffer.from(imageBase64, 'base64');

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `${timestamp}.png`;

    const folder = 'gptimages';
    const s3Key = `${folder}/${fileName}`;

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
      Key: s3Key,
      Body: buffer,
      ContentType: 'image/png',
    }).promise();

    // Return S3 key and URL
    return {
      statusCode: 200,
      body: JSON.stringify({
        s3_key: s3Key,
      }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};
