from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from uuid import UUID
from datetime import datetime
import csv
from io import StringIO
from openpyxl import Workbook
from ..database import get_db
from ..models import Document, DocumentItem, Item, Warehouse, Company
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")



@router.post("/create_document")
async def create_document(db: Session = Depends(get_db)):
    doc_id = uuid.uuid4()
    new_doc = Document(id=doc_id, status='в работе')
    db.add(new_doc)
    db.commit()
    return RedirectResponse(url=f"/document/{doc_id}", status_code=303)







@router.get("/document/{doc_id}", response_class=HTMLResponse)
async def view_document(
    request: Request,
    doc_id: str,
    view_mode: str = Query('detailed'),
    saved: bool = Query(False),
    db: Session = Depends(get_db)
):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    document = db.query(Document).filter(Document.id == doc_id_uuid).first()
    if document is None:
        return HTMLResponse("Документ не найден", status_code=404)

    warehouses = db.query(Warehouse).order_by(Warehouse.name).all()
    companies = db.query(Company).order_by(Company.legal_entity).all()

    if view_mode == 'grouped':
        grouped_items = (
            db.query(
                DocumentItem.item_id.label('item_id'),
                DocumentItem.box_number.label('box_number'),
                func.sum(DocumentItem.quantity).label('total_quantity'),
                Item.skus.label('skus'),
                Item.vendorcode.label('vendorcode'),
                Item.techsize.label('techsize'),
                Item.nmid.label('nmid'),
                Item.subjectname.label('subjectname'),
                Item.length.label('length'),
                Item.width.label('width'),
                Item.height.label('height'),
                Item.company.label('company')
            )
            .join(Item, Item.chrtid == DocumentItem.item_id)
            .filter(DocumentItem.document_id == doc_id_uuid)
            .group_by(
                DocumentItem.item_id,
                DocumentItem.box_number,
                Item.skus,
                Item.vendorcode,
                Item.techsize,
                Item.nmid,
                Item.subjectname,
                Item.length,
                Item.width,
                Item.height,
                Item.company
            )
            .order_by(DocumentItem.box_number.asc(), Item.nmid.asc(), Item.techsize.asc())
            .all()
        )
        return templates.TemplateResponse("document.html", {
            "request": request,
            "doc_id": doc_id,
            "document": document,
            "grouped_items": grouped_items,
            "warehouses": warehouses,
            "companies": companies,
            "view_mode": 'grouped',
            "saved": saved
        })
    else:
        items = db.query(DocumentItem).filter(DocumentItem.document_id == doc_id_uuid).order_by(DocumentItem.line_number.asc()).all()
        return templates.TemplateResponse("document.html", {
            "request": request,
            "doc_id": doc_id,
            "document": document,
            "items": items,
            "warehouses": warehouses,
            "companies": companies,
            "view_mode": 'detailed',
            "saved": saved
        })





@router.post("/document/{doc_id}/update_info")
async def update_document_info(
    doc_id: str,
    document_date: str = Form(None),
    shipping_office: str = Form(None),
    shipping_warehouse: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    document = db.query(Document).filter(Document.id == doc_id_uuid).first()
    if not document:
        return HTMLResponse("Документ не найден", status_code=404)

    if document_date:
        document.document_date = datetime.strptime(document_date, '%Y-%m-%d')
    else:
        document.document_date = None

    document.shipping_office = shipping_office
    document.shipping_warehouse = shipping_warehouse
    db.commit()

    return RedirectResponse(url=f"/document/{doc_id}", status_code=303)






@router.post("/document/{doc_id}/change_status")
async def change_document_status(doc_id: str, new_status: str = Form(...), secret_code: str = Form(None),  db: Session = Depends(get_db)):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    document = db.query(Document).filter(Document.id == doc_id_uuid).first()
    if not document:
        return HTMLResponse("Документ не найден", status_code=404)
    

    # Проверка, если пытаемся вернуть статус "в работе", требуется секретный код
    if new_status == 'в работе':
        # Замените на свой секретный код
        SECRET_CODE = os.getenv('SECRET_KEY')

        if secret_code != SECRET_CODE:
            return JSONResponse({"error": "Неверный секретный код"}, status_code=403)
        

    if new_status in ['в работе', 'отгружен']:
        document.status = new_status
        db.commit()
    else:
        return HTMLResponse("Недопустимый статус", status_code=400)

    return RedirectResponse(url=f"/document/{doc_id}", status_code=303)






@router.post("/document/{doc_id}/add_item")
async def add_item(doc_id: str, skus: str = Form(...), db: Session = Depends(get_db)):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    # Проверка существования документа
    document = db.query(Document).filter(Document.id == doc_id_uuid).first()
    if document is None:
        return HTMLResponse("Документ не найден", status_code=404)
    

    # Поиск товара по штрих-коду
    item = db.query(Item).filter(Item.skus == skus).first()
    if item is None:
         return JSONResponse({"error": "Товар не найден"}, status_code=404)

    # Получаем последнюю запись в документе для определения box_number
    last_item = db.query(DocumentItem).filter(DocumentItem.document_id == doc_id_uuid).order_by(DocumentItem.id.desc()).first()
    box_number = last_item.box_number if last_item and last_item.box_number else 1

    # Определяем следующий номер строки
    last_line_number = (
        db.query(DocumentItem)
        .filter(DocumentItem.document_id == doc_id_uuid)
        .order_by(DocumentItem.line_number.desc())
        .first()
    )
    next_line_number = (last_line_number.line_number + 1) if last_line_number else 1

    # Добавляем новую запись DocumentItem с номером строки
    new_document_item = DocumentItem(
        document_id=doc_id_uuid,
        item_id=item.chrtid,
        quantity=1,
        box_number=box_number,
        line_number=next_line_number
    )
    db.add(new_document_item)
    db.commit()

    return RedirectResponse(url=f"/document/{doc_id}", status_code=303)



@router.post("/document/{doc_id}/delete_item")
async def delete_item(doc_id: str, item_id: int = Form(...), view_mode: str = Query('detailed'), db: Session = Depends(get_db)):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    document_item = db.query(DocumentItem).filter(DocumentItem.id == item_id, DocumentItem.document_id == doc_id_uuid).first()
    if not document_item:
        return HTMLResponse("Товар не найден в документе", status_code=404)

    db.delete(document_item)
    db.commit()

    return RedirectResponse(url=f"/document/{doc_id}?view_mode={view_mode}", status_code=303)




@router.post("/document/{doc_id}/update_quantity")
async def update_quantity(doc_id: str, item_id: int = Form(...), quantity: int = Form(...), view_mode: str = Query('detailed'), db: Session = Depends(get_db)):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    document_item = db.query(DocumentItem).filter(
        DocumentItem.id == item_id,
        DocumentItem.document_id == doc_id_uuid
    ).first()

    if not document_item:
        return HTMLResponse("Товар не найден в документе", status_code=404)

    document_item.quantity = quantity
    db.commit()

    return RedirectResponse(url=f"/document/{doc_id}?view_mode={view_mode}", status_code=303)





@router.post("/document/{doc_id}/update_box_number")
async def update_box_number(doc_id: str, item_id: int = Form(...), box_number: str = Form(None), view_mode: str = Query('detailed'), db: Session = Depends(get_db)):
    # Проверяем наличие документа
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    document = db.query(Document).filter(Document.id == doc_id_uuid).first()
    if not document:
        return HTMLResponse("Документ не найден", status_code=404)

    # Находим запись DocumentItem по ее первичному ключу id
    document_item = db.query(DocumentItem).filter(DocumentItem.id == item_id, DocumentItem.document_id == doc_id_uuid).first()
    if not document_item:
        return HTMLResponse("Товар не найден в документе", status_code=404)

    # Обновляем номер коробки
    document_item.box_number = box_number
    db.commit()

    return RedirectResponse(url=f"/document/{doc_id}?view_mode={view_mode}", status_code=303)



# @router.post("/save_document")
# async def save_document(doc_id: str = Form(...), action: str = Form(...), db: Session = Depends(get_db)):
#     try:
#         doc_id_uuid = uuid.UUID(doc_id)
#     except ValueError:
#         return HTMLResponse("Неверный формат ID документа", status_code=400)

#     # Получаем документ из базы данных
#     document = db.query(Document).filter(Document.id == doc_id_uuid).first()
#     if not document:
#         return HTMLResponse("Документ не найден", status_code=404)

#     # Проверка наличия элементов в документе
#     items_count = db.query(DocumentItem).filter(DocumentItem.document_id == doc_id_uuid).count()

#     # Если документ пустой (нет связанных товаров), удаляем его и возвращаем сообщение
#     if items_count == 0:
#         db.delete(document)
#         db.commit()
#         return HTMLResponse("Документ был пустым и удалён", status_code=200)

#     # Проверка на заполненность обязательных полей
#     if not document.shipping_office or not document.shipping_warehouse:
#         return HTMLResponse("Необходимо заполнить кабинет и склад отгрузки", status_code=400)

#     # Обновляем статус документа, если необходимо
#     document.status = 'saved'
#     db.commit()

#     # Определяем действие после сохранения
#     if action == 'save_exit':
#         return RedirectResponse(url="/", status_code=303)
#     else:
#         return RedirectResponse(url=f"/document/{doc_id}?saved=True", status_code=303)





@router.post("/save_document")
async def save_document(doc_id: str = Form(...), action: str = Form(...), db: Session = Depends(get_db)):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return JSONResponse({"error": "Неверный формат ID документа"}, status_code=400)

    # Получаем документ из базы данных
    document = db.query(Document).filter(Document.id == doc_id_uuid).first()
    if not document:
        return JSONResponse({"error": "Документ не найден"}, status_code=404)

    # Проверка наличия элементов в документе
    items_count = db.query(DocumentItem).filter(DocumentItem.document_id == doc_id_uuid).count()

    if items_count == 0:
        return JSONResponse({"error": "Необходимо добавить товар"}, status_code=400)
    

    # Проверка на заполненность обязательных полей
    if not document.shipping_office or not document.shipping_warehouse:
        return JSONResponse({"error": "Необходимо заполнить кабинет и склад отгрузки"}, status_code=400)


    # Определяем действие после сохранения
    if action == 'save_exit':
        return JSONResponse({"redirect": "/"}, status_code=200)
    else:
        return JSONResponse({"redirect": f"/document/{doc_id}?saved=True"}, status_code=200)



# Функция для очистки документов без товаров
def clean_empty_documents(db: Session):
    # Запрос для удаления документов без связанных элементов
    db.query(Document).filter(
        ~db.query(DocumentItem.document_id).filter(DocumentItem.document_id == Document.id).exists()
    ).delete(synchronize_session=False)
    db.commit()

@router.get("/documents", response_class=HTMLResponse)
async def list_documents(request: Request, db: Session = Depends(get_db)):
    # Очистка документов без товаров перед отображением списка
    clean_empty_documents(db)
    
    # Получаем все документы из базы данных
    documents = db.query(Document).all()
    
    # Рендерим шаблон с переданными документами
    return templates.TemplateResponse("documents.html", {"request": request, "documents": documents})



@router.get("/documents", response_class=HTMLResponse)
async def list_documents(request: Request, db: Session = Depends(get_db)):
    documents = db.query(Document).all()
    return templates.TemplateResponse("documents.html", {"request": request, "documents": documents})



@router.get("/document/{doc_id}/download/csv")
async def download_csv(doc_id: str, db: Session = Depends(get_db)):
    try:
        doc_id_uuid = uuid.UUID(doc_id)
    except ValueError:
        return HTMLResponse("Неверный формат ID документа", status_code=400)

    document = db.query(Document).filter(Document.id == doc_id_uuid).first()
    if not document:
        return HTMLResponse("Документ не найден", status_code=404)

    grouped_items = (
        db.query(
            DocumentItem.item_id.label('item_id'),
            DocumentItem.box_number.label('box_number'),
            func.sum(DocumentItem.quantity).label('total_quantity'),
            Item.skus.label('skus'),
            Item.vendorcode.label('vendorcode'),
            Item.techsize.label('techsize'),
            Item.nmid.label('nmid'),
            Item.subjectname.label('subjectname'),
            Item.length.label('length'),
            Item.width.label('width'),
            Item.height.label('height'),
            Item.company.label('company')
        )
        .join(Item, Item.chrtid == DocumentItem.item_id)
        .filter(DocumentItem.document_id == doc_id_uuid)
        .group_by(
            DocumentItem.item_id,
            DocumentItem.box_number,
            Item.skus,
            Item.vendorcode,
            Item.techsize,
            Item.nmid,
            Item.subjectname,
            Item.length,
            Item.width,
            Item.height,
            Item.company
        )
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ШК', 'Артикул поставщика', 'Размер',
        'Номенклатура ID', 'Предмет', 'Длина', 'Ширина', 'Высота', 'Кабинет',
        'Количество', 'Номер коробки'
    ])
    for item in grouped_items:
        writer.writerow([
            item.skus, item.vendorcode, item.techsize, item.nmid,
            item.subjectname, item.length, item.width, item.height,
            item.company, item.total_quantity, item.box_number
        ])

    output.seek(0)
    headers = {'Content-Disposition': f'attachment; filename="document_{doc_id}.csv"'}
    return StreamingResponse(output, media_type='text/csv', headers=headers)

# @router.get("/document/{doc_id}/download/excel")
# async def download_excel(doc_id: str, db: Session = Depends(get_db)):
#     try:
#         doc_id_uuid = uuid.UUID(doc_id)
#     except ValueError:
#         return HTMLResponse("Неверный формат ID документа", status_code=400)

#     document = db.query(Document).filter(Document.id == doc_id_uuid).first()
#     if not document:
#         return HTMLResponse("Документ не найден", status_code=404)

#     items = db.query(DocumentItem).filter(DocumentItem.document_id == doc_id_uuid).all()

#     wb = Workbook()
#     ws = wb.active
#     ws.title = f"Документ {doc_id}"

#     headers = [
#         'ШК', 'Артикул поставщика', 'Размер', 'Номенклатура ID', 'Предмет',
#         'Длина', 'Ширина', 'Высота', 'Количество', 'Номер коробки'
#     ]
#     ws.append(headers)

#     for item in items:
#         row = [
#             item.item.skus,
#             item.item.vendorcode,
#             item.item.techsize,
#             item.item.nmid,
#             item.item.subjectname,
#             item.item.length,
#             item.item.width,
#             item.item.height,
#             item.quantity,
#             item.box_number or ''
#         ]
#         ws.append(row)

#     output = BytesIO()
#     wb.save(output)
#     output.seek(0)

#     headers = {'Content-Disposition': f'attachment; filename="document_{doc_id}.xlsx"'}
#     return Response(content=output.getvalue(), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)
