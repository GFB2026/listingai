"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

interface Props {
  content: string;
  onChange: (content: string) => void;
}

export function ContentEditor({ content, onChange }: Props) {
  const editor = useEditor({
    extensions: [StarterKit],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getText());
    },
    editorProps: {
      attributes: {
        class:
          "prose prose-sm max-w-none focus:outline-none min-h-[200px] px-4 py-3",
      },
    },
  });

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Toolbar */}
      <div className="flex gap-1 border-b border-gray-200 p-2">
        <button
          onClick={() => editor?.chain().focus().toggleBold().run()}
          className={`rounded px-2 py-1 text-sm ${
            editor?.isActive("bold")
              ? "bg-gray-200 font-bold"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          B
        </button>
        <button
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          className={`rounded px-2 py-1 text-sm italic ${
            editor?.isActive("italic")
              ? "bg-gray-200"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          I
        </button>
        <button
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
          className={`rounded px-2 py-1 text-sm ${
            editor?.isActive("bulletList")
              ? "bg-gray-200"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          List
        </button>
      </div>

      {/* Editor */}
      <EditorContent editor={editor} />
    </div>
  );
}
