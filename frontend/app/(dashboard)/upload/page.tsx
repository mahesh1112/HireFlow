import { Header } from "@/components/layouts/Header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { UploadForm } from "@/components/forms/UploadForm";
import { Info } from "lucide-react";

export default function UploadPage() {
  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title="Upload Resumes"
        subtitle="Bulk upload PDF or DOCX resumes for AI-powered parsing"
      />

      <div className="flex-1 p-8 max-w-4xl mx-auto w-full space-y-6">
        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex gap-3">
          <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">How resume processing works</p>
            <ol className="list-decimal list-inside space-y-1 text-blue-700">
              <li>Upload PDF or DOCX resume files (up to 200 at once)</li>
              <li>
                Gemini AI extracts structured data: skills, experience,
                education, achievements
              </li>
              <li>
                sentence-transformers generate 384-dim embeddings for semantic
                search
              </li>
              <li>
                Resumes are indexed in Pinecone for fast JD matching
              </li>
            </ol>
          </div>
        </div>

        {/* Upload Card */}
        <Card>
          <CardHeader>
            <CardTitle>Bulk Resume Upload</CardTitle>
            <CardDescription>
              Drag and drop up to 200 resume files. Processing happens in the
              background—you can start screening while files are being processed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <UploadForm />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
