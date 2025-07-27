// src/App.test.js
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders TranscriptInput component and checks key elements', () => {
  render(<App />);

  // Check for the title
  const title = screen.getByText(/Transcript Processor/i);
  expect(title).toBeInTheDocument();

  // Check for file input
  const fileInput = screen.getByLabelText(/Choose file/i) || screen.getByTestId('file-input');
  expect(fileInput).toBeInTheDocument();

  // Check for Upload & Transcribe button
  const uploadButton = screen.getByRole('button', { name: /upload & transcribe/i });
  expect(uploadButton).toBeInTheDocument();

  // Check initial status
  const status = screen.getByText(/Ready to Process/i);
  expect(status).toBeInTheDocument();
});
