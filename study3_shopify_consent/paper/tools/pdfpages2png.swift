// Render selected pages of a PDF to PNG with CoreGraphics (no poppler/mupdf on this machine).
// Usage: pdfpages2png in.pdf outprefix dpi [pages]   pages like "1,2,5-7" (default: all)
// Also prints the page count as "PAGES <n>".
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
let a = CommandLine.arguments
guard a.count >= 4, let doc = CGPDFDocument(URL(fileURLWithPath: a[1]) as CFURL) else { print("usage: pdfpages2png in.pdf outprefix dpi [pages]"); exit(1) }
let n = doc.numberOfPages
print("PAGES \(n)")
var pages: [Int] = []
if a.count >= 5 {
  for part in a[4].split(separator: ",") {
    let r = part.split(separator: "-").compactMap { Int($0) }
    if r.count == 2 { pages += Array(r[0]...min(r[1], n)) } else if r.count == 1, r[0] <= n { pages.append(r[0]) }
  }
} else { pages = Array(1...n) }
let dpi = Double(a[3])!
for p in pages {
  guard let page = doc.page(at: p) else { continue }
  let box = page.getBoxRect(.mediaBox)
  let s = dpi / 72.0
  let w = Int((box.width * s).rounded()), h = Int((box.height * s).rounded())
  let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
  ctx.scaleBy(x: s, y: s); ctx.translateBy(x: -box.origin.x, y: -box.origin.y)
  ctx.drawPDFPage(page)
  let out = String(format: "%@-p%02d.png", a[2], p)
  let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: out) as CFURL, UTType.png.identifier as CFString, 1, nil)!
  CGImageDestinationAddImage(dest, ctx.makeImage()!, nil); CGImageDestinationFinalize(dest)
  print(out)
}
