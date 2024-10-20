from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base, engine
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta




class Item(Base):
    __tablename__ = 'carts_content'
    __table_args__ = {'schema': 'report'}

    chrtid = Column(BigInteger, primary_key=True)
    skus = Column(Text)
    techsize = Column(Text)
    wbsize = Column(Text)
    nmid = Column(BigInteger)
    imtid = Column(BigInteger)
    nmuuid = Column(Text)
    subjectid = Column(BigInteger)
    subjectname = Column(Text)
    vendorcode = Column(Text)
    brand = Column(Text)
    title = Column(Text)
    createdat = Column(DateTime)
    updatedat = Column(DateTime)
    length = Column(BigInteger)
    width = Column(BigInteger)
    height = Column(BigInteger)
    company = Column(Text)

    document_items = relationship('DocumentItem', back_populates='item')




class Document(Base):
    __tablename__ = 'documents'
    __table_args__ = {'schema': 'report'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date_created = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=3))
    status = Column(String, nullable=False, default='в работе')

    # Новые поля
    shipping_office = Column(String, nullable=True)
    shipping_warehouse = Column(String, nullable=True)
    document_date = Column(DateTime, nullable=True)

    items = relationship('DocumentItem', back_populates='document')




class DocumentItem(Base):
    __tablename__ = 'document_items'
    __table_args__ = {'schema': 'report'}

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey('report.documents.id', ondelete='CASCADE'))
    item_id = Column(BigInteger, ForeignKey('report.carts_content.chrtid'))
    quantity = Column(Integer, nullable=False)
    box_number = Column(Integer, nullable=True)
    line_number = Column(Integer, nullable=False)  # Новый номер строки

    document = relationship('Document', back_populates='items')
    item = relationship('Item', back_populates='document_items')


class Warehouse(Base):
    __tablename__ = 'warehouses'
    __table_args__ = {'schema': 'report'}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # Добавьте другие поля, если они есть в таблице



class Company(Base):
    __tablename__ = 'company'
    __table_args__ = {'schema': 'report'}

    id = Column(Integer, primary_key=True, index=True)
    legal_entity = Column(String, nullable=False)
    # Добавьте другие поля, если они есть в таблице




# # Удалить зависимую таблицу document_items сначала
# DocumentItem.__table__.drop(engine, checkfirst=True)

# # Затем удалить таблицу documents
# Document.__table__.drop(engine, checkfirst=True)

# # Создать таблицу documents сначала
# Document.__table__.create(engine)

# # Затем создать таблицу document_items
# DocumentItem.__table__.create(engine)




