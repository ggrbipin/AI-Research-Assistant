import ChatBox from "../components/ChatBox";
import Head from "next/head";

export default function Home() {
  return (
    <>
      <Head>
        <title>AI Research Assistant - Intelligent Document Q&A</title>
        <meta name="description" content="AI-powered research assistant with multi-agent workflow" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <ChatBox />
    </>
  );
}
