import Link from "next/link";

export default function Nav() {
  return (
    <nav className="border-b bg-white px-6 py-4 flex gap-6 items-center">
      <span className="font-bold text-lg">JobFinder</span>
      <Link href="/" className="text-sm text-gray-600 hover:text-black">Jobs</Link>
      <Link href="/criteria" className="text-sm text-gray-600 hover:text-black">Criteria</Link>
      <Link href="/settings" className="text-sm text-gray-600 hover:text-black">Settings</Link>
    </nav>
  );
}
