// app/api/upload/route.ts
import { NextResponse } from 'next/server';

export const runtime = 'nodejs';  // Use Node.js runtime for better streaming support

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get('video') as File;

  if (!file) {
    return NextResponse.json(
      { error: 'No video file provided' },
      { status: 400 }
    );
  }

  try {
    // Forward the file to your Azure VM API
    const vmApiUrl = process.env.VM_API_URL + '/upload';
    const buffer = Buffer.from(await file.arrayBuffer());

    const response = await fetch(vmApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
        'X-API-Key': process.env.VM_API_KEY!, // Add authentication if needed
        'X-File-Name': encodeURIComponent(file.name),
      },
      body: buffer,
    });

    if (!response.ok) {
      throw new Error(`VM API responded with ${response.status}`);
    }

    const responseData = await response.json();
    return NextResponse.json(responseData);
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Failed to upload video to storage' },
      { status: 500 }
    );
  }
}